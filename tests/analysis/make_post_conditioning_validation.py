"""Generate a combined post-conditioning volume validation figure
from the four clean Jan 30 2026 sessions (excludes the bad 12:18 startup run)."""
import numpy as np
import matplotlib.pyplot as plt

DATA = {
    0.10: [0.100, 0.098],  # 14:05 _140415
    0.15: [0.148, 0.148],  # 13:53 _135316
    0.20: [0.206, 0.192],  # 12:46 _124518
    0.25: [0.247, 0.251],  # 14:13 _141152
}

xs, ys = [], []
for v, ms in DATA.items():
    for m in ms:
        xs.append(v)
        ys.append(m)
xs = np.array(xs)
ys = np.array(ys)

slope, intercept = np.polyfit(xs, ys, 1)
r2 = 1 - ((ys - (slope * xs + intercept)) ** 2).sum() / ((ys - ys.mean()) ** 2).sum()

targets = sorted(DATA.keys())
means = np.array([np.mean(DATA[t]) for t in targets])
stds = np.array([np.std(DATA[t], ddof=1) if len(DATA[t]) > 1 else 0 for t in targets])

fig, ax = plt.subplots(figsize=(6, 4.5), dpi=150)
xl = np.array([0.08, 0.27])
ax.plot(xl, xl, "k--", lw=1, label="y = x (ideal)")
ax.scatter(xs, ys, s=35, alpha=0.55, color="steelblue", label="Individual replicates")
ax.errorbar(targets, means, yerr=stds, fmt="o", color="darkred", ms=7,
            capsize=4, lw=1.4, label=r"Mean $\pm$ 1$\sigma$")
xf = np.linspace(0.08, 0.27, 50)
ax.plot(xf, slope * xf + intercept, "-", color="darkred", alpha=0.6, lw=1.2,
        label=f"Fit: y = {slope:.3f}x {intercept:+.3f}  ($R^2$={r2:.3f})")
ax.set_xlabel("Target volume (mL)")
ax.set_ylabel("Measured volume (mL)")
ax.set_title("Post-conditioning volume validation (Jan 30, 2026)\n"
             "4 sessions combined, n=2 per target")
ax.grid(True, alpha=0.3)
ax.legend(loc="upper left", fontsize=8)
ax.set_xlim(0.07, 0.28)
ax.set_ylim(0.07, 0.28)
ax.set_aspect("equal")
plt.tight_layout()

out = "output/calibration/aggregate_20260130_142325/post_conditioning_validation.png"
plt.savefig(out)
print(f"Saved: {out}")
print(f"Fit: slope={slope:.4f}, intercept={intercept:+.4f}, R2={r2:.4f}")
for t, me, sd in zip(targets, means, stds):
    bias = (me - t) / t * 100
    cv = sd / me * 100 if me else 0
    print(f"  V_target={t:.2f} mL  measured={me:.4f}+/-{sd:.4f}  bias={bias:+.2f}%  CV={cv:.2f}%")
