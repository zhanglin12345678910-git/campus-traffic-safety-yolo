from pathlib import Path

import pytest

from traffic_api.config import AppSettings, get_settings


def test_get_settings_uses_safe_defaults_without_candidate_model(tmp_path):
    settings = get_settings(env={}, base_dir=tmp_path)

    assert isinstance(settings, AppSettings)
    assert settings.app_name == "安巡智脑"
    assert settings.api_prefix == "/api/v1"
    assert settings.infer_device == "0"
    assert settings.img_size == 640
    assert settings.conf_threshold == 0.3
    assert settings.iou_threshold == 0.5
    assert settings.save_dir == tmp_path / "outputs" / "detections"
    assert settings.model_path is None


def test_get_settings_uses_environment_overrides(tmp_path):
    env = {
        "INFER_DEVICE": "cpu",
        "IMG_SIZE": "1280",
        "CONF_THRESHOLD": "0.45",
        "IOU_THRESHOLD": "0.65",
        "SAVE_DIR": str(tmp_path / "custom-output"),
        "YOLO_MODEL_PATH": str(tmp_path / "models" / "traffic.pt"),
    }

    settings = get_settings(env=env, base_dir=tmp_path)

    assert settings.infer_device == "cpu"
    assert settings.img_size == 1280
    assert settings.conf_threshold == 0.45
    assert settings.iou_threshold == 0.65
    assert settings.save_dir == Path(env["SAVE_DIR"])
    assert settings.model_path == Path(env["YOLO_MODEL_PATH"])


def test_get_settings_accepts_yolo_named_environment_values(tmp_path):
    env = {
        "YOLO_DEVICE": "cpu",
        "YOLO_DEFAULT_IMGSZ": "768",
        "YOLO_DEFAULT_CONF": "0.51",
        "YOLO_DEFAULT_IOU": "0.61",
        "OUTPUT_DIR": "outputs/custom",
        "API_KEY": "secret",
    }

    settings = get_settings(env=env, base_dir=tmp_path)

    assert settings.infer_device == "cpu"
    assert settings.img_size == 768
    assert settings.conf_threshold == 0.51
    assert settings.iou_threshold == 0.61
    assert settings.save_dir == tmp_path / "outputs" / "custom"
    assert settings.api_key == "secret"


def test_get_settings_prefers_yolo_model_path_over_candidates(tmp_path):
    env_model = tmp_path / "override" / "best.pt"
    candidate = (
        tmp_path
        / "runs"
        / "train"
        / "TT100K-增强-yolo11-第一个实验-newt100k2"
        / "weights"
        / "best.pt"
    )
    candidate.parent.mkdir(parents=True)
    candidate.write_text("candidate", encoding="utf-8")

    settings = get_settings(env={"YOLO_MODEL_PATH": str(env_model)}, base_dir=tmp_path)

    assert settings.model_path == env_model


def test_get_settings_selects_first_existing_candidate_model(tmp_path):
    second_candidate = tmp_path / "runs" / "train" / "579-pssm-消融" / "weights" / "best.pt"
    third_candidate = tmp_path / "runs" / "train" / "ASPP-pssm-cctsdb-200e" / "weights" / "best.pt"
    third_candidate.parent.mkdir(parents=True)
    third_candidate.write_text("third", encoding="utf-8")
    second_candidate.parent.mkdir(parents=True)
    second_candidate.write_text("second", encoding="utf-8")

    settings = get_settings(env={}, base_dir=tmp_path)

    assert settings.model_path == second_candidate


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("IMG_SIZE", "large"),
        ("CONF_THRESHOLD", "confident"),
        ("IOU_THRESHOLD", "overlap"),
    ],
)
def test_get_settings_rejects_invalid_numeric_environment_values(tmp_path, name, value):
    with pytest.raises(ValueError, match=name):
        get_settings(env={name: value}, base_dir=tmp_path)
