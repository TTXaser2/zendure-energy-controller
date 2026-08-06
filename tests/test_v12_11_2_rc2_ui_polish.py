import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = (ROOT / 'web_ui.py').read_text(encoding='utf-8')
VER = (ROOT / 'version.py').read_text(encoding='utf-8')

class TestV12112RC2UiPolish(unittest.TestCase):
    def test_version(self):
        self.assertIn('12.11.2-rc20', VER)
        self.assertIn('V12.11.2-RC20', VER)

    def test_redundant_status_header_removed(self):
        self.assertNotIn('Live-Snapshot · Refresh ohne Seitenreload', WEB)
        self.assertIn('id="systemPill" class="zec-system-pill ok"', WEB)

    def test_tooltip_is_bounded_popover(self):
        self.assertIn('data-tooltip=', WEB)
        self.assertIn('max-width:min(360px, calc(100vw - 32px))', WEB)
        self.assertNotIn('class="info-dot" title=', WEB)

    def test_minigraph_has_hover_targets(self):
        self.assertIn('hit_targets_html', WEB)
        self.assertIn('<title>vor ca.', WEB)

    def test_primary_fallbacks_and_graph_xy(self):
        self.assertIn('second_battery_soc_percent', WEB)
        self.assertIn('second_battery_power_w', WEB)
        self.assertIn("data:points.map(x=>({{x:Number(x.minute),y:x.primary_soc}}))", WEB)

    def test_ring_background_and_live_update(self):
        self.assertIn('--zec-ring-inner-bg:var(--zec-card-bg)', WEB)
        self.assertIn("updateRing('primary'", WEB)
        self.assertIn('soc-ring-value', WEB)

    def test_source_status_not_duplicated(self):
        self.assertNotIn('Messquelle aktuell · <span data-zec="source.auto_text">', WEB)

if __name__ == '__main__':
    unittest.main()
