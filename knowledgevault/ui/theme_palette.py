"""Designer theme palettes — Snetch Studio & Papaya inspired."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class ThemePalette:
    name: str
    display_name: str
    is_dark: bool
    bg_primary: str
    bg_secondary: str
    bg_tertiary: str
    bg_elevated: str
    bg_card: str
    bg_card_hover: str
    glass_bg: str
    glass_border: str
    border: str
    border_subtle: str
    text_primary: str
    text_secondary: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_subtle: str
    accent_text: str
    accent_secondary: str
    success: str
    warning: str
    info: str
    graph_note: str
    graph_category: str
    graph_edge: str
    scrollbar: str
    selection: str
    topbar: str
    gradient_start: str
    gradient_end: str


class ThemeId(str, Enum):
    STUDIO = "studio"
    PAPAYA = "papaya"
    ARCTIC = "arctic"
    MIDNIGHT = "midnight"
    NORD = "nord"
    FOREST = "forest"
    SUNSET = "sunset"
    ROSE = "rose"
    OCEAN = "ocean"
    SOLARIZED = "solarized"


def _palette(**kwargs) -> ThemePalette:
    return ThemePalette(**kwargs)


THEMES: dict[ThemeId, ThemePalette] = {
    # Snetch reference — charcoal, magenta CTA, cyan/teal accents
    ThemeId.STUDIO: _palette(
        name="studio", display_name="Studio", is_dark=True,
        bg_primary="#161618", bg_secondary="#1E1E21", bg_tertiary="#28282D",
        bg_elevated="#323238", bg_card="#242428", bg_card_hover="#2C2C32",
        glass_bg="#2A2A30", glass_border="#3A3A44",
        border="#3E3E48", border_subtle="#2E2E36",
        text_primary="#F4F4F8", text_secondary="#A8A8B8", text_muted="#68687A",
        accent="#FF3D9A", accent_hover="#E82E88", accent_subtle="#3D1830",
        accent_text="#FF6BB5", accent_secondary="#00E5C3",
        success="#00E5C3", warning="#FFB830", info="#8B7CF8",
        graph_note="#FF3D9A", graph_category="#00E5C3", graph_edge="#3A3A48",
        scrollbar="#48485A", selection="#4A2040", topbar="#1A1A1D",
        gradient_start="#FF3D9A", gradient_end="#C026D3",
    ),
    # Papaya reference — deep indigo, purple glow
    ThemeId.PAPAYA: _palette(
        name="papaya", display_name="Papaya", is_dark=True,
        bg_primary="#0F0F18", bg_secondary="#14141F", bg_tertiary="#1C1C2B",
        bg_elevated="#26263A", bg_card="#18182A", bg_card_hover="#202035",
        glass_bg="#22223A", glass_border="#35355A",
        border="#35355A", border_subtle="#252540",
        text_primary="#F8F8FF", text_secondary="#B0B0D0", text_muted="#7070A0",
        accent="#BF5AF2", accent_hover="#A347E0", accent_subtle="#2D1848",
        accent_text="#D8A0FF", accent_secondary="#5E5CE6",
        success="#30D158", warning="#FF9F0A", info="#64D2FF",
        graph_note="#BF5AF2", graph_category="#64D2FF", graph_edge="#35355A",
        scrollbar="#404060", selection="#3A1860", topbar="#12121C",
        gradient_start="#BF5AF2", gradient_end="#5E5CE6",
    ),
    ThemeId.ARCTIC: _palette(
        name="arctic", display_name="Arctic", is_dark=False,
        bg_primary="#F4F6FA", bg_secondary="#FFFFFF", bg_tertiary="#EEF1F7",
        bg_elevated="#FFFFFF", bg_card="#FFFFFF", bg_card_hover="#F8FAFD",
        glass_bg="#FFFFFF", glass_border="#E2E8F0",
        border="#D8DEE9", border_subtle="#E8ECF3",
        text_primary="#0F172A", text_secondary="#475569", text_muted="#94A3B8",
        accent="#6366F1", accent_hover="#4F46E5", accent_subtle="#EEF2FF",
        accent_text="#4F46E5", accent_secondary="#0D9488",
        success="#059669", warning="#D97706", info="#3B82F6",
        graph_note="#6366F1", graph_category="#059669", graph_edge="#D8DEE9",
        scrollbar="#CBD5E1", selection="#C7D2FE", topbar="#FFFFFF",
        gradient_start="#6366F1", gradient_end="#8B5CF6",
    ),
    ThemeId.MIDNIGHT: _palette(
        name="midnight", display_name="Midnight", is_dark=True,
        bg_primary="#09090F", bg_secondary="#101018", bg_tertiary="#181820",
        bg_elevated="#20202C", bg_card="#14141C", bg_card_hover="#1C1C28",
        glass_bg="#1C1C28", glass_border="#2C2C3C",
        border="#2C2C3C", border_subtle="#1C1C28",
        text_primary="#EEEEF4", text_secondary="#9898A8", text_muted="#5C5C6E",
        accent="#7C7CFF", accent_hover="#6565E8", accent_subtle="#22224A",
        accent_text="#A5A5FF", accent_secondary="#4ECDC4",
        success="#4ECDC4", warning="#F0C040", info="#5B9CF6",
        graph_note="#7C7CFF", graph_category="#4ECDC4", graph_edge="#2C2C3C",
        scrollbar="#3A3A48", selection="#2A2A5A", topbar="#0C0C14",
        gradient_start="#7C7CFF", gradient_end="#5B9CF6",
    ),
    ThemeId.NORD: _palette(
        name="nord", display_name="Nord", is_dark=True,
        bg_primary="#2E3440", bg_secondary="#3B4252", bg_tertiary="#434C5E",
        bg_elevated="#4C566A", bg_card="#3B4252", bg_card_hover="#434C5E",
        glass_bg="#434C5E", glass_border="#4C566A",
        border="#4C566A", border_subtle="#3B4252",
        text_primary="#ECEFF4", text_secondary="#D8DEE9", text_muted="#81A1C1",
        accent="#88C0D0", accent_hover="#81A1C1", accent_subtle="#2E3A44",
        accent_text="#88C0D0", accent_secondary="#A3BE8C",
        success="#A3BE8C", warning="#EBCB8B", info="#5E81AC",
        graph_note="#88C0D0", graph_category="#A3BE8C", graph_edge="#4C566A",
        scrollbar="#4C566A", selection="#3B4F5C", topbar="#3B4252",
        gradient_start="#88C0D0", gradient_end="#5E81AC",
    ),
    ThemeId.FOREST: _palette(
        name="forest", display_name="Forest", is_dark=True,
        bg_primary="#0A100E", bg_secondary="#101816", bg_tertiary="#182220",
        bg_elevated="#1E2A28", bg_card="#141E1C", bg_card_hover="#1A2624",
        glass_bg="#1A2624", glass_border="#283832",
        border="#283832", border_subtle="#182220",
        text_primary="#E4EEE8", text_secondary="#98B8A8", text_muted="#5A8070",
        accent="#3DD68C", accent_hover="#2BB872", accent_subtle="#0F2820",
        accent_text="#6EE7A8", accent_secondary="#38BDF8",
        success="#3DD68C", warning="#F0C040", info="#38BDF8",
        graph_note="#3DD68C", graph_category="#38BDF8", graph_edge="#283832",
        scrollbar="#384842", selection="#0F3528", topbar="#101816",
        gradient_start="#3DD68C", gradient_end="#38BDF8",
    ),
    ThemeId.SUNSET: _palette(
        name="sunset", display_name="Sunset", is_dark=True,
        bg_primary="#120C0A", bg_secondary="#1A1210", bg_tertiary="#221A18",
        bg_elevated="#2A2220", bg_card="#1E1614", bg_card_hover="#261E1C",
        glass_bg="#261E1C", glass_border="#38302C",
        border="#38302C", border_subtle="#221A18",
        text_primary="#F5EDE8", text_secondary="#C0A090", text_muted="#806860",
        accent="#FF7043", accent_hover="#E85A30", accent_subtle="#3D1E14",
        accent_text="#FFAB88", accent_secondary="#F472B6",
        success="#66BB6A", warning="#FFD54F", info="#F472B6",
        graph_note="#FF7043", graph_category="#F472B6", graph_edge="#38302C",
        scrollbar="#484038", selection="#4A2010", topbar="#1A1210",
        gradient_start="#FF7043", gradient_end="#F472B6",
    ),
    ThemeId.ROSE: _palette(
        name="rose", display_name="Rose", is_dark=False,
        bg_primary="#FAF4F5", bg_secondary="#FFFFFF", bg_tertiary="#F5EAEC",
        bg_elevated="#FFFFFF", bg_card="#FFFFFF", bg_card_hover="#FBF0F2",
        glass_bg="#FFFFFF", glass_border="#E8D0D6",
        border="#E8D0D6", border_subtle="#F0E0E4",
        text_primary="#1A0A10", text_secondary="#5C3040", text_muted="#9A7080",
        accent="#E8367A", accent_hover="#C82060", accent_subtle="#FFF0F3",
        accent_text="#E8367A", accent_secondary="#7C3AED",
        success="#059669", warning="#D97706", info="#7C3AED",
        graph_note="#E8367A", graph_category="#059669", graph_edge="#E8D0D6",
        scrollbar="#E8D0D6", selection="#FFD6E4", topbar="#FFFFFF",
        gradient_start="#E8367A", gradient_end="#C82060",
    ),
    ThemeId.OCEAN: _palette(
        name="ocean", display_name="Ocean", is_dark=False,
        bg_primary="#EEF5F8", bg_secondary="#FFFFFF", bg_tertiary="#E4EFF5",
        bg_elevated="#FFFFFF", bg_card="#FFFFFF", bg_card_hover="#F0F7FA",
        glass_bg="#FFFFFF", glass_border="#C8DDE8",
        border="#C8DDE8", border_subtle="#DCE9F0",
        text_primary="#0A2840", text_secondary="#2D6080", text_muted="#6B9AB0",
        accent="#0891B2", accent_hover="#0E7490", accent_subtle="#E0F7FA",
        accent_text="#0891B2", accent_secondary="#059669",
        success="#059669", warning="#D97706", info="#2563EB",
        graph_note="#0891B2", graph_category="#059669", graph_edge="#C8DDE8",
        scrollbar="#C8DDE8", selection="#A5F3FC", topbar="#FFFFFF",
        gradient_start="#0891B2", gradient_end="#2563EB",
    ),
    ThemeId.SOLARIZED: _palette(
        name="solarized", display_name="Solarized", is_dark=True,
        bg_primary="#002B36", bg_secondary="#073642", bg_tertiary="#0A3E4C",
        bg_elevated="#0E4452", bg_card="#073642", bg_card_hover="#0A3E4C",
        glass_bg="#0A3E4C", glass_border="#134E5C",
        border="#134E5C", border_subtle="#073642",
        text_primary="#FDF6E3", text_secondary="#93A1A1", text_muted="#657B83",
        accent="#2AA198", accent_hover="#268BD2", accent_subtle="#0A3E4C",
        accent_text="#2AA198", accent_secondary="#859900",
        success="#859900", warning="#CB4B16", info="#268BD2",
        graph_note="#2AA198", graph_category="#859900", graph_edge="#134E5C",
        scrollbar="#134E5C", selection="#0A4A52", topbar="#073642",
        gradient_start="#2AA198", gradient_end="#268BD2",
    ),
}


def get_palette(theme_id: ThemeId) -> ThemePalette:
    return THEMES[theme_id]
