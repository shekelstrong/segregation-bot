import importlib
import unittest

from PIL import Image


def load_animations():
    try:
        return importlib.import_module("segregation_video.animations")
    except ModuleNotFoundError as exc:
        raise AssertionError("segregation_video.animations is not implemented") from exc


class InterpolatePositionsTests(unittest.TestCase):
    def test_includes_start_and_end_positions(self):
        animations = load_animations()

        positions = animations.interpolate_positions(10, 0, frame_count=3)

        self.assertEqual(positions, [10, 5, 0])

    def test_rejects_non_positive_frame_count(self):
        animations = load_animations()

        with self.assertRaisesRegex(ValueError, "frame_count"):
            animations.interpolate_positions(0, 10, frame_count=0)


class TransactionSlideTests(unittest.TestCase):
    def test_slides_next_screen_in_from_the_right(self):
        animations = load_animations()
        current = Image.new("RGBA", (4, 2), "red")
        next_screen = Image.new("RGBA", (4, 2), "blue")

        frames = list(
            animations.generate_transaction_slide_frames(
                current,
                next_screen,
                frame_count=3,
            )
        )

        try:
            self.assertEqual([frame.size for frame in frames], [(4, 2)] * 3)
            self.assertEqual(frames[0].getpixel((3, 0)), (255, 0, 0, 255))
            self.assertEqual(frames[1].getpixel((1, 0)), (255, 0, 0, 255))
            self.assertEqual(frames[1].getpixel((2, 0)), (0, 0, 255, 255))
            self.assertEqual(frames[-1].getpixel((0, 0)), (0, 0, 255, 255))
        finally:
            for frame in frames:
                frame.close()
            current.close()
            next_screen.close()

    def test_rejects_screens_with_different_sizes(self):
        animations = load_animations()
        current = Image.new("RGBA", (4, 2), "red")
        next_screen = Image.new("RGBA", (5, 2), "blue")

        try:
            with self.assertRaisesRegex(ValueError, "same size"):
                list(
                    animations.generate_transaction_slide_frames(
                        current,
                        next_screen,
                    )
                )
        finally:
            current.close()
            next_screen.close()


class DetailsSlideTests(unittest.TestCase):
    def test_slides_details_up_to_the_bottom_edge(self):
        animations = load_animations()
        transaction_screen = Image.new("RGBA", (4, 4), "red")
        details_screen = Image.new("RGBA", (4, 2), "blue")

        frames = list(
            animations.generate_details_slide_frames(
                transaction_screen,
                details_screen,
                details_height=2,
                frame_count=3,
            )
        )

        try:
            self.assertEqual([frame.size for frame in frames], [(4, 4)] * 3)
            self.assertEqual(frames[0].getpixel((0, 3)), (255, 0, 0, 255))
            self.assertEqual(frames[1].getpixel((0, 2)), (255, 0, 0, 255))
            self.assertEqual(frames[1].getpixel((0, 3)), (0, 0, 255, 255))
            self.assertEqual(frames[-1].getpixel((0, 1)), (255, 0, 0, 255))
            self.assertEqual(frames[-1].getpixel((0, 2)), (0, 0, 255, 255))
        finally:
            for frame in frames:
                frame.close()
            transaction_screen.close()
            details_screen.close()

    def test_rejects_details_height_outside_background(self):
        animations = load_animations()
        transaction_screen = Image.new("RGBA", (4, 4), "red")
        details_screen = Image.new("RGBA", (4, 2), "blue")

        try:
            with self.assertRaisesRegex(ValueError, "details_height"):
                list(
                    animations.generate_details_slide_frames(
                        transaction_screen,
                        details_screen,
                        details_height=5,
                    )
                )
        finally:
            transaction_screen.close()
            details_screen.close()


if __name__ == "__main__":
    unittest.main()
