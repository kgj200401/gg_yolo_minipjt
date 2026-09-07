"""Read-only label/prediction audit. Writes diagnostic figures, never source labels."""
import json
import argparse
import csv
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".yolo-config"))
import numpy as np
from PIL import Image, ImageDraw
from ultralytics import YOLO


def ious(a, b):
    if not len(a) or not len(b):
        return np.zeros((len(a), len(b)))
    low = np.maximum(a[:, None, :2], b[None, :, :2])
    high = np.minimum(a[:, None, 2:], b[None, :, 2:])
    inter = np.maximum(high-low, 0).prod(2)
    area_a = (a[:, 2:]-a[:, :2]).prod(1)
    area_b = (b[:, 2:]-b[:, :2]).prod(1)
    return inter/(area_a[:, None]+area_b[None, :]-inter+1e-9)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["train", "valid"], default="valid")
    args = parser.parse_args()
    out = ROOT / ("runs/data_audit" if args.split == "valid" else "runs/data_audit_train")
    out.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(ROOT / "runs/detect/ozm_augmented/weights/best.pt"))
    image_dir = ROOT / "dataset" / args.split / "images"
    paths = sorted(image_dir.iterdir())
    results = model.predict([str(p) for p in paths], conf=0.25, iou=0.7, imgsz=640,
                            rect=False, batch=16, device=0, verbose=False, stream=True)
    records = []
    for path, result in zip(paths, results):
        h, w = result.orig_shape
        label_path = ROOT / "dataset" / args.split / "labels" / (path.stem+'.txt')
        labels = np.array([list(map(float, s.split())) for s in label_path.read_text().splitlines()]).reshape(-1,5)
        gt = np.column_stack((labels[:,1:3]-labels[:,3:5]/2,labels[:,1:3]+labels[:,3:5]/2))*[w,h,w,h]
        pred = result.boxes.xyxy.cpu().numpy()
        cls = result.boxes.cls.cpu().numpy()
        conf = result.boxes.conf.cpu().numpy()
        overlap = ious(gt, pred)
        matches = np.array(np.nonzero((overlap>=.5)&(labels[:,0,None]==cls)&(conf>=.7))).T
        if len(matches)>1:
            matches = matches[overlap[matches[:,0],matches[:,1]].argsort()[::-1]]
            matches = matches[np.unique(matches[:,1],return_index=True)[1]]
            matches = matches[np.unique(matches[:,0],return_index=True)[1]]
        matched_gt = set(matches[:,0]) if len(matches) else set()
        matched_pred = set(matches[:,1]) if len(matches) else set()
        misses=[]
        for i,row in enumerate(labels):
            if i in matched_gt: continue
            same = np.where(cls==row[0])[0]
            j = int(same[np.argmax(overlap[i,same])]) if len(same) else None
            misses.append(dict(class_name=model.names[int(row[0])],
                               best_same_iou=float(overlap[i,j]) if j is not None else 0,
                               best_same_conf=float(conf[j]) if j is not None else 0))
        fp=[int(i) for i in np.where(conf>=.7)[0] if i not in matched_pred]
        record=dict(file=path.name, tp=len(matches), fp=len(fp), fn=len(misses), misses=misses,
                    gt=labels.tolist(), boxes=gt.tolist(), predictions=[dict(box=box.tolist(),
                    name=model.names[int(c)],confidence=float(s)) for box,c,s in zip(pred,cls,conf)])
        records.append(record)
    ranked=sorted(records,key=lambda r:r['fn']+2*r['fp'],reverse=True)
    for page in range(3):
        canvas=Image.new('RGB',(1200,4*340),'white'); draw=ImageDraw.Draw(canvas)
        for slot,r in enumerate(ranked[page*4:(page+1)*4]):
            y=slot*340
            draw.text((8,y+2),f"#{page*4+slot+1} TP={r['tp']} FP={r['fp']} FN={r['fn']} {r['file'][:72]}",fill='black')
            im=Image.open(image_dir/r['file']).convert('RGB')
            scale=min(590/im.width,300/im.height)
            im=im.resize((int(im.width*scale),int(im.height*scale)))
            for col in range(2): canvas.paste(im,(col*600,y+30))
            for label,box in zip(r['gt'],r['boxes']):
                coords=[box[0]*scale,y+30+box[1]*scale,box[2]*scale,y+30+box[3]*scale]
                draw.rectangle(coords,outline='lime',width=2)
                draw.text((coords[0],coords[1]),model.names[int(label[0])],fill='lime',stroke_width=1,stroke_fill='black')
            for p in r['predictions']:
                box=p['box']; color='red' if p['confidence']>=.7 else 'orange'
                coords=[600+box[0]*scale,y+30+box[1]*scale,600+box[2]*scale,y+30+box[3]*scale]
                draw.rectangle(coords,outline=color,width=2)
                draw.text((coords[0],coords[1]),f"{p['name']} {p['confidence']:.2f}",fill=color,stroke_width=1,stroke_fill='black')
        canvas.save(out/f'errors_{page+1}.png')
    (out/'audit.json').write_text(json.dumps(ranked,indent=2),encoding='utf-8')
    with (out/'review_queue.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['rank', 'file', 'tp', 'fp', 'fn', 'status'])
        for rank, record in enumerate(ranked, 1):
            if record['fp'] or record['fn']:
                writer.writerow([rank, record['file'], record['tp'], record['fp'], record['fn'], 'needs_review'])
    print('Images audited:',len(records),'Totals:',{k:sum(r[k] for r in records) for k in ['tp','fp','fn']})
    print('Misses with same-class box IoU>=.5 but confidence<.7:',sum(m['best_same_iou']>=.5 and m['best_same_conf']<.7 for r in records for m in r['misses']))
    print('Figures:',out)


if __name__=='__main__':
    main()
