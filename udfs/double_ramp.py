import matplotlib as mpl
import matplotlib.patches as patches
import numpy as np


def rm_eb(ax):
    r2 = patches.Rectangle((-10, -0.172), 20, 1.344, fc="white", ec="white", alpha=1.00)
    r3 = patches.Rectangle(
        (-10, -0.172), 20, 4 * 0.344, fc="white", ec="white", alpha=1.00
    )

    rotate = mpl.transforms.Affine2D().rotate_deg(30)
    translate_p = mpl.transforms.Affine2D().translate(0, 0.344 / np.cos(np.radians(30)))
    translate_m = mpl.transforms.Affine2D().translate(
        0, -4 * 0.344 / np.cos(np.radians(30))
    )
    r2.set_transform(rotate + translate_p + ax.transData)
    r3.set_transform(rotate + translate_m + ax.transData)

    # r1 = patches.Rectangle((-10,-0.172), 20, 0.344, fc="blue", alpha=0.50)
    # r1.set_transform(rotate+ax.transData)
    # ax.add_patch(r1)
    ax.add_patch(r2)
    ax.add_patch(r3)

    return ax
