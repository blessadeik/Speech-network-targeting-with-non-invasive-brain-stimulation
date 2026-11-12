import numpy as np
import pytest

import utils as U


def sphere_points(r=90.0, n=4000, seed=0):
    rng = np.random.default_rng(seed)
    v = rng.normal(size=(n, 3))
    return r * v / np.linalg.norm(v, axis=1, keepdims=True)


def test_tangent_basis_is_orthonormal_and_outward_on_lateral_scalp():
    pts = sphere_points()
    c = np.array([-90.0, 0.0, 0.0])            # lateral point: world x/y offsets fail here
    u, v, n = U.local_tangent_basis(pts, c)
    assert np.allclose([u @ u, v @ v, n @ n], 1, atol=1e-6)
    assert abs(u @ v) < 1e-6 and abs(u @ n) < 1e-6
    assert n @ (c / np.linalg.norm(c)) > 0.98   # outward
    ring = U.ring_points(c, u, v, 40.0, 4)
    d = [np.linalg.norm(p - c) for p in ring]
    assert np.allclose(d, 40.0)


def test_ring_projected_to_scalp_keeps_four_distinct_sites():
    pts = sphere_points(n=20000)
    c = U.nearest_point(pts, [-90, 0, 0])
    u, v, _ = U.local_tangent_basis(pts, c)
    proj = [U.nearest_point(pts, p) for p in U.ring_points(c, u, v, 40.0, 4)]
    dists = [np.linalg.norm(a - b) for i, a in enumerate(proj) for b in proj[i + 1:]]
    assert min(dists) > 40.0                   # world-xy offsets would collapse pairs


def test_triangle_areas_sum_to_surface_area():
    xyz = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], float)
    tri = np.array([[0, 1, 2], [1, 3, 2]])
    a = U.triangle_node_areas(xyz, tri)
    assert np.isclose(a.sum(), 1.0)
    n = U.triangle_node_normals(xyz, tri)
    assert np.allclose(np.abs(n[:, 2]), 1.0)


def test_weighted_quantile_matches_unweighted_median():
    x = np.arange(1, 102, dtype=float)
    assert np.isclose(U.weighted_quantile(x, np.ones_like(x), 0.5), 51.0)
    assert U.weighted_quantile(np.array([1.0, 10.0]), np.array([9.0, 1.0]), 0.5) < 5


def test_rotate_matsimnibs_preserves_axis_and_orthonormality():
    m = np.eye(4); m[:3, 3] = [10, 20, 30]
    r = U.rotate_matsimnibs(m, 90)
    assert np.allclose(r[:3, 2], m[:3, 2]) and np.allclose(r[:3, 3], m[:3, 3])
    assert np.allclose(r[:3, :3].T @ r[:3, :3], np.eye(3))
    assert np.allclose(r[:3, 0], [0, 1, 0])


def test_tissue_lengths_along_ray():
    lab = np.zeros((40, 1, 1), int); lab[0:10] = 2; lab[10:20] = 3; lab[20:30] = 7; lab[30:40] = 5
    seg = U.tissue_lengths_along_ray(lab, np.eye(4), [0, 0, 0], [39.999, 0, 0])
    assert seg[3] == pytest.approx(10, abs=0.5) and seg[7] == pytest.approx(10, abs=0.5)


def test_atlas_mask_tolerant_matching_and_length_check():
    atlas = {"lh.L_44_ROI": np.array([1, 0, 0, 0], bool), "lh.L_45_ROI": np.array([0, 1, 0, 0], bool),
             "rh.R_44_ROI": np.array([0, 0, 1, 0], bool)}
    m = U._atlas_mask(atlas, ["L_44", "L_45"], 4)
    assert m.tolist() == [True, True, False, False]
    with pytest.raises(KeyError):
        U._atlas_mask(atlas, ["L_99"], 4)
    with pytest.raises(ValueError):
        U._atlas_mask(atlas, ["L_44"], 5)


def test_head_info_parses_ids_without_cohort_table():
    assert U.head_info("IXI-012_deface")["face_metrics"] is False
    assert U.head_info("IXI-012_full")["face_metrics"] is True
    i = U.head_info("ARC-M2001_lesion")
    assert i["group"] == "lesioned" and i["version"] == "lesion"
    assert U.default_cond_set("ARC-M2001_lesion", None) == "lesion_csf"
    assert U.default_cond_set("ARC-M2001_filled", None) is None
    assert U.head_info("ernie")["face_metrics"] is True


def test_s07_roi_metrics_ratio_and_focality():
    import s07_extract_roi_metrics as S7
    magn = np.array([1.0, 1.0, 0.2, 0.2, 0.1]); areas = np.full(5, 100.0)
    m = S7.roi_metrics(magn, None, areas, np.array([1, 1, 0, 0, 0], bool),
                       np.array([0, 0, 1, 1, 0], bool), whole_p999=1.0)
    assert np.isclose(m["ratio_on_off"], 5.0) and np.isclose(m["focality_area_cm2"], 2.0)
