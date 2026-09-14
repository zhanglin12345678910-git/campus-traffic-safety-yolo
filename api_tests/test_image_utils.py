import builtins
import sys

import pytest

from traffic_api.image_utils import (
    decode_image_bytes,
    encode_image_jpeg,
    ensure_rgb_or_bgr_image,
    get_image_info,
    save_image,
)
from traffic_api.schemas import ImageInfo


class ShapeOnlyImage:
    def __init__(self, shape):
        self.shape = shape


def test_get_image_info_reads_color_shape():
    image = ShapeOnlyImage((480, 640, 3))

    assert get_image_info(image) == ImageInfo(width=640, height=480, channels=3)


def test_get_image_info_reads_grayscale_shape_as_one_channel():
    image = ShapeOnlyImage((240, 320))

    assert get_image_info(image) == ImageInfo(width=320, height=240, channels=1)


@pytest.mark.parametrize("shape", [(10, 20), (10, 20, 3)])
def test_ensure_rgb_or_bgr_image_accepts_2d_or_three_channel_shapes(shape):
    image = ShapeOnlyImage(shape)

    assert ensure_rgb_or_bgr_image(image) is image


@pytest.mark.parametrize(
    "image",
    [
        object(),
        ShapeOnlyImage(()),
        ShapeOnlyImage((10,)),
        ShapeOnlyImage((10, 20, 1)),
        ShapeOnlyImage((10, 20, 4)),
        ShapeOnlyImage((10, 20, 3, 1)),
    ],
)
def test_ensure_rgb_or_bgr_image_rejects_missing_or_invalid_shape(image):
    with pytest.raises(ValueError):
        ensure_rgb_or_bgr_image(image)


def test_decode_image_bytes_reports_missing_cv2_dependency(monkeypatch):
    real_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "cv2":
            raise ImportError("cv2 unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)

    with pytest.raises(RuntimeError, match="cv2"):
        decode_image_bytes(b"not an image")


def test_encode_image_jpeg_uses_lazy_cv2_import(monkeypatch):
    class EncodedBytes:
        def tobytes(self):
            return b"jpeg-bytes"

    class FakeCv2:
        def imencode(self, extension, image):
            assert extension == ".jpg"
            assert image.shape == (10, 20, 3)
            return True, EncodedBytes()

    monkeypatch.setitem(sys.modules, "cv2", FakeCv2())

    assert encode_image_jpeg(ShapeOnlyImage((10, 20, 3))) == b"jpeg-bytes"


def test_save_image_creates_parent_directory_and_calls_cv2(monkeypatch, tmp_path):
    calls = []

    class FakeCv2:
        def imwrite(self, path, image):
            calls.append((path, image))
            return True

    monkeypatch.setitem(sys.modules, "cv2", FakeCv2())
    image = ShapeOnlyImage((10, 20, 3))
    output_path = tmp_path / "nested" / "sign.jpg"

    save_image(image, output_path)

    assert output_path.parent.is_dir()
    assert calls == [(str(output_path), image)]
