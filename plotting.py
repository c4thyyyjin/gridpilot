"""Plot helpers; importing this module does not initialize Matplotlib."""
import textwrap
import numpy as np


def plot_pareto(frame, output_path, color="#2a7ab9", baseline_color="#888888"):
    """Label close points together, using a separate column and leader lines.

    Only annotations are grouped; the plotted data points are never averaged.
    Returns figure/axes for inspection and closes the figure if rendering fails.
    """
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    try:
        fig.subplots_adjust(left=.12, right=.68, bottom=.15, top=.87)
        finite = frame[np.isfinite(frame.co2) & np.isfinite(frame.cost)]
        ax.plot(finite.co2, finite.cost / 1000, "o-", color=color, label="MPC at different λ")
        if len(frame) and np.isfinite(frame.base_co2.iloc[0]) and np.isfinite(frame.base_cost.iloc[0]):
            ax.plot(frame.base_co2.iloc[0], frame.base_cost.iloc[0] / 1000,
                    "s", color=baseline_color, ms=8, label="observed-demand baseline")
        ax.set(xlabel="CO₂ over 72 h (tonnes)", ylabel="Electricity cost (k CNY)",
               title="Cost vs carbon: feasible schedules")
        ax.legend(loc="upper left", fontsize=8)
        fig.canvas.draw()
        groups = []
        for _, row in finite.iterrows():
            xy = (float(row.co2), float(row.cost) / 1000)
            pixel = ax.transData.transform(xy)
            group = next((g for g in groups if np.linalg.norm(pixel - g["pixel"]) <= 12), None)
            if group is None:
                group = {"xy": xy, "pixel": pixel, "lambdas": []}
                groups.append(group)
            group["lambdas"].append(float(row["lambda"]))
        groups.sort(key=lambda g: g["xy"][1], reverse=True)
        slots = np.linspace(.88, .08, len(groups)) if len(groups) > 1 else [.5]
        for group, y in zip(groups, slots):
            values = ", ".join(f"{v:g}" for v in sorted(group["lambdas"]))
            label = textwrap.fill("λ = " + values, width=25)
            ax.annotate(label, group["xy"], xycoords="data", xytext=(1.05, y),
                        textcoords="axes fraction", ha="left", va="center", fontsize=8,
                        bbox=dict(boxstyle="round,pad=.3", fc="white", ec="#dddddd"),
                        arrowprops=dict(arrowstyle="-", color="#777777", lw=.7),
                        annotation_clip=False)
        fig.savefig(output_path, bbox_inches="tight")
        return fig, ax
    except Exception:
        plt.close(fig)
        raise
