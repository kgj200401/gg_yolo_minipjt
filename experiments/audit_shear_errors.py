"""Capture per-image errors through the same validator used in reported metrics."""
import json
from pathlib import Path
from PIL import Image, ImageDraw
from evaluate_model import ROOT, YOLO, DetectionValidator
from ultralytics.utils import ops
from ultralytics.utils.metrics import box_iou

OUT = ROOT/'runs/shear_error_audit'


class AuditValidator(DetectionValidator):
    records = []

    def update_metrics(self, preds, batch):
        for si, pred in enumerate(preds):
            gt = self._prepare_batch(si,batch)
            tp = self._process_batch(pred,gt)['tp'][:,0]
            overlap = box_iou(gt['bboxes'],pred['bboxes']).cpu().numpy()
            def scale(boxes):
                return ops.scale_boxes(gt['imgsz'],boxes.clone(),gt['ori_shape'],gt['ratio_pad']).cpu().tolist()
            boxes = scale(pred['bboxes'])
            classes = pred['cls'].cpu().tolist()
            targets = gt['cls'].cpu().tolist()
            predictions=[]
            for i,(box,c,conf) in enumerate(zip(boxes,classes,pred['conf'].cpu().tolist())):
                best = int(overlap[:,i].argmax()) if len(targets) else None
                same = [j for j,x in enumerate(targets) if x==c]
                same_best = max(same,key=lambda j:overlap[j,i]) if same else None
                predictions.append(dict(box=box,name=self.names[int(c)],conf=conf,tp=bool(tp[i]),
                    closest_gt=self.names[int(targets[best])] if best is not None else None,
                    closest_iou=float(overlap[best,i]) if best is not None else 0,
                    same_iou=float(overlap[same_best,i]) if same_best is not None else 0))
            type(self).records.append(dict(file=Path(gt['im_file']).name,path=gt['im_file'],
                gt=[dict(box=b,name=self.names[int(c)]) for b,c in zip(scale(gt['bboxes']),targets)],
                predictions=predictions,tp=int(tp.sum()),fp=int((~tp).sum()),fn=len(targets)-int(tp.sum())))
        return super().update_metrics(preds,batch)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    all_records={}
    for label,run,reference in [('A','ozm_augmented','reference_shear0'),('H','ozm_shear0','validation_shear0')]:
        AuditValidator.records=[]
        YOLO(str(ROOT/'runs/detect'/run/'weights/best.pt')).val(
            data=str(ROOT/'dataset_corrected_v2/data.yaml'),split='val',device=0,imgsz=640,
            batch=16,workers=0,conf=.65,iou=.7,plots=False,verbose=False,
            project=str(OUT),name=label,validator=AuditValidator)
        records=AuditValidator.records
        expected=next(x for x in json.loads((ROOT/'runs'/reference/'report.json').read_text())['results'] if x['confidence']==.65)
        totals={k:sum(r[k] for r in records) for k in ['tp','fp','fn']}
        assert totals=={k:expected[k] for k in totals},(label,totals,expected)
        all_records[label]={r['file']:r for r in records}
        print(label,totals,flush=True)
    (OUT/'records.json').write_text(json.dumps(all_records,indent=2),encoding='utf-8')
    ranked=sorted([r for r in all_records['H'].values() if r['fp']],
                  key=lambda r:(r['fp']-all_records['A'][r['file']]['fp'],r['fp']),reverse=True)
    for i,row in enumerate(ranked,1):
        with Image.open(row['path']) as source: im=source.convert('RGB')
        scale=min(480/im.width,450/im.height)
        im=im.resize((int(im.width*scale),int(im.height*scale)))
        canvas=Image.new('RGB',(1440,im.height+65),'white');draw=ImageDraw.Draw(canvas)
        draw.text((5,3),f"{i}: {row['file']}",fill='black')
        for col,label in enumerate(['GT','A','H']):
            dx=col*480;canvas.paste(im,(dx,65))
            record=row if label=='GT' else all_records[label][row['file']]
            title=label if label=='GT' else f"{label} TP={record['tp']} FP={record['fp']} FN={record['fn']}"
            draw.text((dx+5,25),title,fill='black')
            items=record['gt'] if label=='GT' else record['predictions']
            for j,p in enumerate(items):
                b=p['box'];coords=[dx+b[0]*scale,65+b[1]*scale,dx+b[2]*scale,65+b[3]*scale]
                color='lime' if label=='GT' or p['tp'] else 'red'
                draw.rectangle(coords,outline=color,width=2)
                text=p['name'] if label=='GT' else f"#{j} {p['name']} {p['conf']:.2f}"
                draw.text((coords[0],coords[1]),text,fill=color,stroke_width=1,stroke_fill='black')
        canvas.save(OUT/f'case_{i:02}.png')
    (OUT/'case_index.json').write_text(json.dumps([dict(case=i,file=r['file'],A_fp=all_records['A'][r['file']]['fp'],H_fp=r['fp']) for i,r in enumerate(ranked,1)],indent=2),encoding='utf-8')
    print('Cases:',len(ranked),flush=True)


if __name__=='__main__':
    main()
