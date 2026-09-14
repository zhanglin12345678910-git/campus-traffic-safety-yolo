import pytest

from traffic_api.config import AppSettings
from traffic_api.exceptions import ModelNotConfiguredError
from traffic_api.inference_service import TrafficSignDetector


class ShapeOnlyImage:
    shape = (64, 96, 3)


class TensorLike:
    def __init__(self, value):
        self.value = value

    def cpu(self):
        return self

    def numpy(self):
        return self

    def tolist(self):
        return self.value


class FakeBoxes:
    cls = TensorLike([0])
    conf = TensorLike([0.77])
    xyxy = TensorLike([[1, 2, 3, 4]])

    def __len__(self):
        return 1


class FakeYoloResult:
    names = {0: "sign"}
    boxes = FakeBoxes()
    orig_img = ShapeOnlyImage()

    def plot(self):
        return ShapeOnlyImage()


class FakeYolo:
    created_with = []

    def __init__(self, model_path):
        self.model_path = model_path
        self.predict_calls = []
        FakeYolo.created_with.append(model_path)

    def predict(self, image, **kwargs):
        self.predict_calls.append((image, kwargs))
        return [FakeYoloResult()]


def make_settings(tmp_path, model_path=None):
    return AppSettings(
        app_name="安巡智脑",
        api_prefix="/api/v1",
        infer_device="cpu",
        img_size=640,
        conf_threshold=0.3,
        iou_threshold=0.5,
        save_dir=tmp_path,
        model_path=model_path,
    )


def test_detector_raises_clear_error_when_model_path_missing(tmp_path):
    detector = TrafficSignDetector(settings=make_settings(tmp_path, model_path=None), yolo_cls=FakeYolo)

    with pytest.raises(ModelNotConfiguredError, match="YOLO_MODEL_PATH"):
        detector.get_model()


def test_detector_loads_model_once_and_reuses_it(tmp_path):
    model_path = tmp_path / "best.pt"
    model_path.write_bytes(b"fake")
    FakeYolo.created_with.clear()
    detector = TrafficSignDetector(settings=make_settings(tmp_path, model_path=model_path), yolo_cls=FakeYolo)

    first = detector.get_model()
    second = detector.get_model()

    assert first is second
    assert detector.load_count == 1
    assert FakeYolo.created_with == [str(model_path)]


def test_detector_detect_image_returns_prediction_output(tmp_path):
    model_path = tmp_path / "best.pt"
    model_path.write_bytes(b"fake")
    detector = TrafficSignDetector(settings=make_settings(tmp_path, model_path=model_path), yolo_cls=FakeYolo)

    output = detector.detect_image(ShapeOnlyImage())

    assert output.detection_result.detections[0].class_name == "sign"
    assert output.detection_result.image.width == 96
    assert output.visual_image is not None
