"""Generate unique colour-coded SVG illustrations for homepage cards."""

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "static" / "home"


def write_svg(name: str, accent: str, body: str) -> None:
    content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 360" role="img" aria-hidden="true">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#10151c" stop-opacity="0.85"/>
    </linearGradient>
  </defs>
  <rect width="640" height="360" rx="28" fill="url(#bg)"/>
  <rect x="18" y="18" width="604" height="324" rx="22" fill="none" stroke="{accent}" stroke-opacity="0.35" stroke-width="2"/>
  {body}
</svg>
"""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(content, encoding="utf-8")
    print(name)


def main() -> None:
    write_svg(
        "zones.svg",
        "#7dd3c0",
        """
  <g fill="#7dd3c0" fill-opacity="0.85">
    <rect x="90" y="70" width="140" height="100" rx="14"/>
    <rect x="250" y="70" width="140" height="100" rx="14" fill-opacity="0.55"/>
    <rect x="410" y="70" width="140" height="100" rx="14" fill-opacity="0.7"/>
    <rect x="90" y="190" width="220" height="100" rx="14" fill-opacity="0.45"/>
    <rect x="330" y="190" width="220" height="100" rx="14" fill-opacity="0.65"/>
  </g>
  <circle cx="160" cy="120" r="18" fill="#10151c" fill-opacity="0.45"/>
  <circle cx="440" cy="240" r="18" fill="#10151c" fill-opacity="0.45"/>
""",
    )

    write_svg(
        "project-list.svg",
        "#5b8def",
        """
  <rect x="110" y="70" width="420" height="52" rx="12" fill="#5b8def" fill-opacity="0.9"/>
  <rect x="110" y="140" width="420" height="52" rx="12" fill="#5b8def" fill-opacity="0.6"/>
  <rect x="110" y="210" width="420" height="52" rx="12" fill="#5b8def" fill-opacity="0.35"/>
  <circle cx="145" cy="96" r="12" fill="#10151c" fill-opacity="0.5"/>
  <circle cx="145" cy="166" r="12" fill="#10151c" fill-opacity="0.5"/>
  <circle cx="145" cy="236" r="12" fill="#10151c" fill-opacity="0.5"/>
  <rect x="180" y="88" width="220" height="16" rx="6" fill="#10151c" fill-opacity="0.35"/>
  <rect x="180" y="158" width="180" height="16" rx="6" fill="#10151c" fill-opacity="0.35"/>
  <rect x="180" y="228" width="250" height="16" rx="6" fill="#10151c" fill-opacity="0.35"/>
""",
    )

    write_svg(
        "project-roadmap.svg",
        "#5b8def",
        """
  <g stroke="#5b8def" stroke-opacity="0.25" stroke-width="2">
    <line x1="120" y1="60" x2="120" y2="300"/>
    <line x1="240" y1="60" x2="240" y2="300"/>
    <line x1="360" y1="60" x2="360" y2="300"/>
    <line x1="480" y1="60" x2="480" y2="300"/>
  </g>
  <rect x="130" y="90" width="220" height="36" rx="10" fill="#5b8def"/>
  <rect x="200" y="155" width="260" height="36" rx="10" fill="#5b8def" fill-opacity="0.7"/>
  <rect x="150" y="220" width="180" height="36" rx="10" fill="#5b8def" fill-opacity="0.45"/>
  <circle cx="360" cy="108" r="10" fill="#f5d76e"/>
  <circle cx="450" cy="173" r="10" fill="#f5d76e"/>
""",
    )

    write_svg(
        "architecture-list.svg",
        "#f0a202",
        """
  <g fill="#f0a202">
    <rect x="120" y="80" width="120" height="80" rx="12" fill-opacity="0.95"/>
    <rect x="260" y="80" width="120" height="80" rx="12" fill-opacity="0.65"/>
    <rect x="400" y="80" width="120" height="80" rx="12" fill-opacity="0.4"/>
    <rect x="120" y="190" width="120" height="80" rx="12" fill-opacity="0.55"/>
    <rect x="260" y="190" width="120" height="80" rx="12" fill-opacity="0.8"/>
    <rect x="400" y="190" width="120" height="80" rx="12" fill-opacity="0.5"/>
  </g>
""",
    )

    write_svg(
        "architecture-diagram.svg",
        "#f0a202",
        """
  <g stroke="#f0a202" stroke-width="3" fill="none" stroke-opacity="0.7">
    <line x1="200" y1="120" x2="320" y2="200"/>
    <line x1="440" y1="120" x2="320" y2="200"/>
    <line x1="320" y1="200" x2="220" y2="280"/>
    <line x1="320" y1="200" x2="420" y2="280"/>
  </g>
  <circle cx="200" cy="120" r="34" fill="#f0a202"/>
  <circle cx="440" cy="120" r="34" fill="#f0a202" fill-opacity="0.7"/>
  <circle cx="320" cy="200" r="40" fill="#f0a202" fill-opacity="0.9"/>
  <circle cx="220" cy="280" r="28" fill="#f0a202" fill-opacity="0.55"/>
  <circle cx="420" cy="280" r="28" fill="#f0a202" fill-opacity="0.55"/>
""",
    )

    write_svg(
        "architecture-model.svg",
        "#f0a202",
        """
  <rect x="220" y="50" width="200" height="48" rx="12" fill="#f0a202"/>
  <line x1="320" y1="98" x2="320" y2="140" stroke="#f0a202" stroke-width="3"/>
  <line x1="160" y1="140" x2="480" y2="140" stroke="#f0a202" stroke-width="3"/>
  <line x1="160" y1="140" x2="160" y2="170" stroke="#f0a202" stroke-width="3"/>
  <line x1="320" y1="140" x2="320" y2="170" stroke="#f0a202" stroke-width="3"/>
  <line x1="480" y1="140" x2="480" y2="170" stroke="#f0a202" stroke-width="3"/>
  <rect x="90" y="170" width="140" height="42" rx="10" fill="#f0a202" fill-opacity="0.75"/>
  <rect x="250" y="170" width="140" height="42" rx="10" fill="#f0a202" fill-opacity="0.75"/>
  <rect x="410" y="170" width="140" height="42" rx="10" fill="#f0a202" fill-opacity="0.75"/>
  <rect x="100" y="250" width="55" height="55" rx="8" fill="#f0a202" fill-opacity="0.4"/>
  <rect x="165" y="250" width="55" height="55" rx="8" fill="#f0a202" fill-opacity="0.4"/>
  <rect x="260" y="250" width="55" height="55" rx="8" fill="#f0a202" fill-opacity="0.4"/>
  <rect x="325" y="250" width="55" height="55" rx="8" fill="#f0a202" fill-opacity="0.4"/>
  <rect x="420" y="250" width="55" height="55" rx="8" fill="#f0a202" fill-opacity="0.4"/>
  <rect x="485" y="250" width="55" height="55" rx="8" fill="#f0a202" fill-opacity="0.4"/>
""",
    )

    write_svg(
        "architecture-roadmap.svg",
        "#f0a202",
        """
  <g stroke="#f0a202" stroke-opacity="0.25" stroke-width="2">
    <line x1="140" y1="60" x2="140" y2="300"/>
    <line x1="260" y1="60" x2="260" y2="300"/>
    <line x1="380" y1="60" x2="380" y2="300"/>
    <line x1="500" y1="60" x2="500" y2="300"/>
  </g>
  <rect x="150" y="100" width="280" height="40" rx="10" fill="#f0a202"/>
  <rect x="200" y="180" width="240" height="40" rx="10" fill="#f0a202" fill-opacity="0.65"/>
  <polygon points="260,95 268,112 286,112 272,124 278,142 260,132 242,142 248,124 234,112 252,112" fill="#f5d76e"/>
  <polygon points="380,175 388,192 406,192 392,204 398,222 380,212 362,222 368,204 354,192 372,192" fill="#f5d76e"/>
""",
    )

    write_svg(
        "risk-list.svg",
        "#e85d4c",
        """
  <polygon points="160,80 210,160 110,160" fill="#e85d4c"/>
  <rect x="240" y="100" width="280" height="28" rx="8" fill="#e85d4c" fill-opacity="0.85"/>
  <polygon points="160,180 210,260 110,260" fill="#e85d4c" fill-opacity="0.65"/>
  <rect x="240" y="200" width="240" height="28" rx="8" fill="#e85d4c" fill-opacity="0.55"/>
  <polygon points="160,250 190,300 130,300" fill="#e85d4c" fill-opacity="0.35"/>
""",
    )

    write_svg(
        "cost-dashboard.svg",
        "#3cb371",
        """
  <g fill="#3cb371">
    <rect x="120" y="180" width="60" height="100" rx="8" fill-opacity="0.9"/>
    <rect x="120" y="140" width="60" height="40" rx="8" fill-opacity="0.55"/>
    <rect x="220" y="120" width="60" height="160" rx="8" fill-opacity="0.9"/>
    <rect x="220" y="80" width="60" height="40" rx="8" fill-opacity="0.55"/>
    <rect x="320" y="150" width="60" height="130" rx="8" fill-opacity="0.9"/>
    <rect x="320" y="110" width="60" height="40" rx="8" fill-opacity="0.55"/>
    <rect x="420" y="100" width="60" height="180" rx="8" fill-opacity="0.9"/>
    <rect x="420" y="60" width="60" height="40" rx="8" fill-opacity="0.55"/>
  </g>
  <line x1="100" y1="290" x2="520" y2="290" stroke="#3cb371" stroke-opacity="0.4" stroke-width="3"/>
""",
    )

    write_svg(
        "budget-list.svg",
        "#3cb371",
        """
  <rect x="150" y="60" width="340" height="240" rx="18" fill="#3cb371" fill-opacity="0.2" stroke="#3cb371" stroke-width="3"/>
  <rect x="180" y="95" width="280" height="24" rx="8" fill="#3cb371" fill-opacity="0.9"/>
  <rect x="180" y="140" width="200" height="18" rx="6" fill="#3cb371" fill-opacity="0.55"/>
  <rect x="180" y="175" width="240" height="18" rx="6" fill="#3cb371" fill-opacity="0.45"/>
  <rect x="180" y="210" width="160" height="18" rx="6" fill="#3cb371" fill-opacity="0.35"/>
  <circle cx="430" cy="250" r="28" fill="#3cb371"/>
  <text x="430" y="258" text-anchor="middle" font-size="24" font-family="Segoe UI, sans-serif" fill="#10151c" font-weight="700">£</text>
""",
    )

    write_svg(
        "run-contract-list.svg",
        "#3cb371",
        """
  <rect x="180" y="50" width="280" height="260" rx="16" fill="#3cb371" fill-opacity="0.25" stroke="#3cb371" stroke-width="3"/>
  <rect x="210" y="90" width="220" height="18" rx="6" fill="#3cb371"/>
  <rect x="210" y="130" width="180" height="14" rx="5" fill="#3cb371" fill-opacity="0.6"/>
  <rect x="210" y="160" width="200" height="14" rx="5" fill="#3cb371" fill-opacity="0.45"/>
  <rect x="210" y="190" width="160" height="14" rx="5" fill="#3cb371" fill-opacity="0.35"/>
  <rect x="210" y="240" width="70" height="36" rx="8" fill="#3cb371"/>
  <text x="245" y="264" text-anchor="middle" font-size="14" font-family="Segoe UI, sans-serif" fill="#10151c" font-weight="800">PO</text>
""",
    )

    write_svg(
        "run-contract-roadmap.svg",
        "#3cb371",
        """
  <g stroke="#3cb371" stroke-opacity="0.25" stroke-width="2">
    <line x1="120" y1="60" x2="120" y2="300"/>
    <line x1="240" y1="60" x2="240" y2="300"/>
    <line x1="360" y1="60" x2="360" y2="300"/>
    <line x1="480" y1="60" x2="480" y2="300"/>
  </g>
  <rect x="130" y="120" width="250" height="44" rx="10" fill="#3cb371"/>
  <rect x="380" y="120" width="100" height="44" rx="10" fill="#3cb371" fill-opacity="0.35" stroke="#3cb371" stroke-dasharray="6 4"/>
  <rect x="130" y="200" width="22" height="22" rx="4" fill="#10151c" stroke="#3cb371" stroke-width="2"/>
  <rect x="250" y="200" width="22" height="22" rx="4" fill="#10151c" stroke="#3cb371" stroke-width="2"/>
  <text x="141" y="216" font-size="9" font-family="Segoe UI, sans-serif" fill="#3cb371" font-weight="800">PO</text>
  <text x="261" y="216" font-size="9" font-family="Segoe UI, sans-serif" fill="#3cb371" font-weight="800">PO</text>
""",
    )

    write_svg(
        "about.svg",
        "#8fa0b5",
        """
  <rect x="160" y="70" width="320" height="220" rx="18" fill="#8fa0b5" fill-opacity="0.25" stroke="#8fa0b5" stroke-width="3"/>
  <circle cx="320" cy="140" r="36" fill="#8fa0b5"/>
  <text x="320" y="152" text-anchor="middle" font-size="36" font-family="Georgia, serif" fill="#10151c" font-weight="700">i</text>
  <rect x="220" y="200" width="200" height="16" rx="6" fill="#8fa0b5" fill-opacity="0.7"/>
  <rect x="240" y="230" width="160" height="14" rx="6" fill="#8fa0b5" fill-opacity="0.45"/>
""",
    )

    print("done", len(list(OUT.glob("*.svg"))))


if __name__ == "__main__":
    main()
