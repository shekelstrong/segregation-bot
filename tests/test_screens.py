"""
test_screens.py — дополнительные тесты для кандидатских модулей.

README раздел 14 рекомендует покрыть тестами:
  - разбор двух строк;
  - правила валидации;
  - расчёт количества кадров;
  - крайние кадры свайпа;
  - очистку временных файлов при ошибке.

Эти тесты дополняют существующие из tests/test_animations.py
(которые я не трогал — README раздел 14 их запрещает удалять).
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Делаем корень проекта видимым для импортов
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from segregation_video import (  # noqa: E402
    build_state_1_blue,
    build_state_2_pink,
    build_state_3_transaction,
    build_state_4_details,
    expected_duration_seconds,
    format_number_for_display,
    parse_user_message,
    render_to_tempfile,
    safe_delete,
    total_frame_count,
)
from segregation_video.parse_input import (  # noqa: E402
    NAME_MAX_LEN,
    NUMBER_MAX_LEN,
    ParsedUserData,
    UserInputError,
)
from segregation_video.swipe import generate_card_swipe_frames  # noqa: E402
from segregation_video.timeline import build_complete_timeline  # noqa: E402


# ---------------------------------------------------------------------------
# Разбор двух строк
# ---------------------------------------------------------------------------


class ParseUserMessageTests(unittest.TestCase):
    def test_valid_two_lines(self):
        u = parse_user_message("Carlos Vinicio Barrios Quiroa\n170120010184")
        self.assertEqual(u.name, "Carlos Vinicio Barrios Quiroa")
        self.assertEqual(u.number, "170120010184")

    def test_strips_whitespace(self):
        u = parse_user_message("  Иван Иванов  \n  482913  ")
        self.assertEqual(u.name, "Иван Иванов")
        self.assertEqual(u.number, "482913")

    def test_normalizes_number(self):
        # Пробелы и дефисы в номере удаляются
        u = parse_user_message("Test Name\n170-120-010-184")
        self.assertEqual(u.number, "170120010184")
        u = parse_user_message("Test Name\n170 120 010 184")
        self.assertEqual(u.number, "170120010184")

    def test_rejects_empty(self):
        with self.assertRaises(UserInputError):
            parse_user_message("")
        with self.assertRaises(UserInputError):
            parse_user_message("   \n   \n   ")

    def test_rejects_too_few_lines(self):
        with self.assertRaises(UserInputError):
            parse_user_message("Only one line")

    def test_rejects_too_many_lines(self):
        with self.assertRaises(UserInputError):
            parse_user_message("Line 1\nLine 2\nLine 3")

    def test_rejects_short_name(self):
        with self.assertRaises(UserInputError):
            parse_user_message("A\n12345")

    def test_rejects_long_name(self):
        long_name = "A" * (NAME_MAX_LEN + 1)
        with self.assertRaises(UserInputError):
            parse_user_message(f"{long_name}\n12345")

    def test_rejects_letters_in_number(self):
        with self.assertRaises(UserInputError):
            parse_user_message("Ivan Ivanov\n1234abc5678")

    def test_rejects_short_number(self):
        with self.assertRaises(UserInputError):
            parse_user_message("Ivan Ivanov\n12")

    def test_rejects_long_number(self):
        long_number = "1" * (NUMBER_MAX_LEN + 1)
        with self.assertRaises(UserInputError):
            parse_user_message(f"Ivan Ivanov\n{long_number}")

    def test_rejects_pure_digits_as_name(self):
        with self.assertRaises(UserInputError):
            parse_user_message("12345\n67890")


class FormatNumberForDisplayTests(unittest.TestCase):
    def test_groups_by_three(self):
        self.assertEqual(format_number_for_display("170120010184"), "170 120 010 184")

    def test_short_number(self):
        self.assertEqual(format_number_for_display("1234"), "1 234")

    def test_with_spaces_and_dashes(self):
        self.assertEqual(
            format_number_for_display("170-120-010-184"), "170 120 010 184"
        )


# ---------------------------------------------------------------------------
# Расчёт количества кадров и длительности
# ---------------------------------------------------------------------------


class FrameCountTests(unittest.TestCase):
    def test_total_frame_count_is_605(self):
        # Эталон ровно 605 кадров @ 60fps = 10.08s
        self.assertEqual(total_frame_count(), 605)

    def test_expected_duration(self):
        self.assertAlmostEqual(expected_duration_seconds(60), 605 / 60, places=2)

    def test_timeline_has_correct_length(self):
        # НЕ материализуем таймлайн в список — 605 кадров × 9 МБ ≈ 5 ГБ и OOM.
        # Считаем через enumerate, итератор держит в памяти ≤ 1 кадр за раз.
        u = ParsedUserData(name="Test User", number="123456")
        count = sum(1 for _ in build_complete_timeline(u))
        self.assertEqual(count, total_frame_count())


# ---------------------------------------------------------------------------
# Свайп — крайние кадры
# ---------------------------------------------------------------------------


class CardSwipeEdgeFramesTests(unittest.TestCase):
    def _make_screen(self, color):
        from PIL import Image
        return Image.new("RGB", (1180, 2556), color)

    def test_first_frame_is_current(self):
        current = self._make_screen("red")
        nxt = self._make_screen("blue")
        try:
            frames = list(
                generate_card_swipe_frames(
                    current, nxt, frame_count=5
                )
            )
            self.assertEqual(len(frames), 5)
            # На первом кадре current_card должна быть полностью видна,
            # а next_card — за пределами frame справа.
            first = frames[0].convert("RGB")
            # Проверяем что центральный пиксель — это цвет current (red)
            cx, cy = 1180 // 2, 2556 // 2
            r, g, b = first.getpixel((cx, cy))[:3]
            self.assertGreater(r, 200)
            self.assertLess(g, 50)
            self.assertLess(b, 50)
            first.close()
        finally:
            current.close()
            nxt.close()

    def test_last_frame_is_next(self):
        current = self._make_screen("red")
        nxt = self._make_screen("blue")
        try:
            frames = list(
                generate_card_swipe_frames(
                    current, nxt, frame_count=5
                )
            )
            # На последнем кадре current_card должна быть уехать влево,
            # а next_card — на своём месте.
            last = frames[-1].convert("RGB")
            cx, cy = 1180 // 2, 2556 // 2
            r, g, b = last.getpixel((cx, cy))[:3]
            self.assertLess(r, 50)
            self.assertGreater(b, 200)
            last.close()
        finally:
            current.close()
            nxt.close()

    def test_rejects_different_sizes(self):
        from PIL import Image
        a = Image.new("RGB", (1180, 2556), "red")
        b = Image.new("RGB", (1000, 2556), "blue")
        try:
            with self.assertRaises(ValueError):
                list(generate_card_swipe_frames(a, b, frame_count=3))
        finally:
            a.close()
            b.close()

    def test_rejects_non_positive_count(self):
        from PIL import Image
        a = Image.new("RGB", (1180, 2556), "red")
        b = Image.new("RGB", (1180, 2556), "blue")
        try:
            with self.assertRaises(ValueError):
                list(generate_card_swipe_frames(a, b, frame_count=0))
        finally:
            a.close()
            b.close()


# ---------------------------------------------------------------------------
# Сборка визуальных состояний — размер
# ---------------------------------------------------------------------------


class StateSizeTests(unittest.TestCase):
    """Все четыре состояния должны вернуть кадр строго (1180, 2556)."""

    def setUp(self):
        self.user = ParsedUserData(name="Carlos Vinicio", number="170120010184")

    def test_blue(self):
        im = build_state_1_blue()
        try:
            self.assertEqual(im.size, (1180, 2556))
        finally:
            im.close()

    def test_pink(self):
        im = build_state_2_pink()
        try:
            self.assertEqual(im.size, (1180, 2556))
        finally:
            im.close()

    def test_transaction(self):
        im = build_state_3_transaction(self.user)
        try:
            self.assertEqual(im.size, (1180, 2556))
        finally:
            im.close()

    def test_details(self):
        im = build_state_4_details(self.user)
        try:
            self.assertEqual(im.size, (1180, 2556))
        finally:
            im.close()


# ---------------------------------------------------------------------------
# Очистка временных файлов
# ---------------------------------------------------------------------------


class TempFileCleanupTests(unittest.TestCase):
    def test_safe_delete_removes_existing_file(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            path = f.name
        self.assertTrue(os.path.exists(path))
        safe_delete(path)
        self.assertFalse(os.path.exists(path))

    def test_safe_delete_handles_missing_file(self):
        # Не существующий файл — не должно быть исключения
        safe_delete("/tmp/this/does/not/exist_xyz.mp4")
        safe_delete(None)

    def test_render_cleans_up_on_failure(self):
        """Если encode падает — временный файл удаляется."""
        u = ParsedUserData(name="Test", number="123456")
        tmp_dir = Path(tempfile.gettempdir()) / "segregation_video"
        before = (
            {p.name for p in tmp_dir.glob("result_*.mp4")}
            if tmp_dir.exists() else set()
        )
        # Подменяем iter_encode, чтобы он бросил исключение.
        with mock.patch(
            "segregation_video.service.iter_encode_visually_lossless_from_pil",
            side_effect=RuntimeError("ffmpeg boom"),
        ):
            with self.assertRaises(RuntimeError):
                render_to_tempfile(u)
        # Не должно появиться новых файлов result_*.mp4 в каталоге рендера.
        after = (
            {p.name for p in tmp_dir.glob("result_*.mp4")}
            if tmp_dir.exists() else set()
        )
        new_files = after - before
        self.assertEqual(
            new_files, set(),
            f"фейковый render оставил файлы: {new_files}",
        )


if __name__ == "__main__":
    unittest.main()