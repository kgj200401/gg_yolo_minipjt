"""Plot actual training records; no training or model changes."""
import csv
import json
from pathlib import Path
from statistics import mean
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'runs/training_curve_analysis'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    fig, axes = plt.subplots(2,3,figsize=(15,8))
    keys = ['train/cls_loss','val/cls_loss','val/box_loss','train/box_loss','metrics/mAP50-95(B)','lr/pg0']
    summary = {}
    for name,run,windows in [('A','ozm_augmented',[(111,120),(127,136),(137,146)]),
                             ('E','ozm_lr0005',[(91,100),(116,125)])]:
        with (ROOT/'runs/detect'/run/'results.csv').open() as f:
            rows = [{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
        summary[name] = {f'{lo}-{hi}':{k:mean(r[k] for r in rows if lo<=r['epoch']<=hi) for k in keys}
                         for lo,hi in windows}
        best = max(rows,key=lambda r:r['metrics/mAP50-95(B)'])['epoch']
        for ax,key in zip(axes.flat,keys):
            line, = ax.plot([r['epoch'] for r in rows],[r[key] for r in rows],alpha=.2)
            ax.plot([r['epoch'] for r in rows],
                    [mean(x[key] for x in rows[max(0,i-9):i+1]) for i in range(len(rows))],
                    color=line.get_color(),label=f'{name}: trailing 10-epoch mean')
            ax.axvline(best,color=line.get_color(),ls=':',alpha=.5)
            ax.set_title(key); ax.set_xlabel('Epoch'); ax.grid(alpha=.2)
    axes[0,0].legend()
    fig.suptitle('A vs E: original training validation labels; dotted lines = best epoch')
    fig.tight_layout()
    fig.savefig(OUT/'curves.png',dpi=150)
    plt.close(fig)
    (OUT/'windows.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(OUT)


if __name__ == '__main__':
    main()
