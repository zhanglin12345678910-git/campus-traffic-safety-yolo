from traffic_api.config import AppSettings
from traffic_api.inference_core import prediction_result_to_detection_result, run_prediction


class ShapeOnlyImage:
    shape = (480, 640, 3)


class TensorLike:
    def __init__(self, value):
        self.value = value

    def cpu(self):
        return self

    def numpy(self):
        return self

    def astype(self, _dtype):
        return self

    def tolist(self):
        return self.value


class FakeBoxes:
    def __init__(self):
        self.cls = TensorLike([2, 5])
        self.conf = TensorLike([0.63, 0.91])
        self.xyxy = TensorLike([[1.2, 2.4, 30.0, 40.0], [10.0, 20.0, 70.0, 90.0]])

    def __len__(self):
        return 2


class FakeYoloResult:
    names = {2: "warning", 5: "stop"}

    def __init__(self):
        self.boxes = FakeBoxes()
        self.orig_img = ShapeOnlyImage()
        self.plotted = ShapeOnlyImage()

    def plot(self):
        return self.plotted


class FakeModel:
    def __init__(self):
        self.calls = []

    def predict(self, image, **kwargs):
        self.calls.append((image, kwargs))
        return [FakeYoloResult()]


def make_settings(tmp_path):
    return AppSettings(
        app_name="安巡智脑",
        api_prefix="/api/v1",
        infer_device="cpu",
        img_size=512,
        conf_threshold=0.42,
        iou_threshold=0.55,
        save_dir=tmp_path,
        model_path=tmp_path / "best.pt",
    )


def test_prediction_result_to_detection_result_converts_boxes_and_names():
    result = prediction_result_to_detection_result(FakeYoloResult(), image=ShapeOnlyImage(), elapsed_ms=12.5)

    assert result.image.width == 640
    assert result.image.height == 480
    assert result.elapsed_ms == 12.5
    assert [d.class_name for d in result.detections] == ["warning", "stop"]
    assert result.detections[1].class_id == 5
    assert result.detections[1].confidence == 0.91
    assert result.detections[1].box_xyxy == (10.0, 20.0, 70.0, 90.0)


def test_run_prediction_passes_settings_to_model_and_returns_visual(tmp_path):
    model = FakeModel()
    image = ShapeOnlyImage()
    output = run_prediction(model, image, make_settings(tmp_path))

    assert model.calls == [
        (
            image,
            {
                "device": "cpu",
                "imgsz": 512,
                "conf": 0.42,
                "iou": 0.55,
                "verbose": False,
            },
        )
    ]
    assert output.visual_image is output.raw_result.plotted
    assert output.detection_result.detections[0].class_name == "warning"
    assert output.elapsed_ms >= 0

