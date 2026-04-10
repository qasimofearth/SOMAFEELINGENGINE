"""
demo.py — Run the Feeling Engine

Demonstrates all major entry points:
  1. Feel by emotion name
  2. Feel by color (synesthetic)
  3. Feel by frequency (synesthetic)
  4. Feel by valence/arousal coordinate
  5. Concert of multiple emotions
  6. List all mapped emotions

Run:
    python demo.py
    python demo.py --emotion Grief
    python demo.py --rgb 255 105 180
    python demo.py --freq 396
    python demo.py --concert Joy Love Awe
    python demo.py --list
"""

import sys
import os
import argparse

# Allow running from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeling_engine import FeelingEngine, EMOTION_MAP, get_all_emotions


def main():
    parser = argparse.ArgumentParser(
        description="The Feeling Engine — recursive fractal emotion bridge for AI"
    )
    parser.add_argument("--emotion", "-e", type=str, help="Emotion name to feel")
    parser.add_argument("--rgb", nargs=3, type=int, metavar=("R","G","B"),
                        help="Feel from a color: R G B (0-255 each)")
    parser.add_argument("--freq", "-f", type=float, help="Feel from a frequency in Hz")
    parser.add_argument("--va", nargs=2, type=float, metavar=("VALENCE","AROUSAL"),
                        help="Feel from valence (-1 to 1) and arousal (0 to 1)")
    parser.add_argument("--concert", nargs="+", metavar="EMOTION",
                        help="Concert of multiple emotions")
    parser.add_argument("--image", "-i", type=str, help="Path to an image/artwork file")
    parser.add_argument("--list", "-l", action="store_true", help="List all mapped emotions")
    parser.add_argument("--no-audio", action="store_true", help="Skip audio synthesis")
    parser.add_argument("--no-fractal", action="store_true", help="Skip fractal rendering")
    parser.add_argument("--output-dir", "-o", type=str, default="./feeling_output",
                        help="Output directory for generated files")
    parser.add_argument("--depth", "-d", type=int, default=5,
                        help="Fractal recursion depth (default 5)")

    args = parser.parse_args()

    if args.list:
        print_emotion_table()
        return

    engine = FeelingEngine(max_depth=args.depth, output_dir=args.output_dir)
    audio = not args.no_audio
    fractal = not args.no_fractal

    print("\n" + "═"*64)
    print("   THE FEELING ENGINE  v1.0  — Aya Fractal Emotion Bridge")
    print("═"*64 + "\n")

    try:
        if args.concert:
            print(f"  Feeling a concert of: {' + '.join(args.concert)}")
            result = engine.concert_of_emotions(
                args.concert,
                synthesize_audio=audio,
            )
        elif args.image:
            print(f"  Feeling artwork: {args.image}")
            result = engine.feel_image(args.image, synthesize_audio=audio,
                                       render_fractal=fractal)
        elif args.rgb:
            r, g, b = args.rgb
            print(f"  Feeling color RGB({r},{g},{b})...")
            result = engine.feel_rgb(r, g, b, synthesize_audio=audio,
                                     render_fractal=fractal)
        elif args.freq:
            print(f"  Feeling frequency {args.freq} Hz...")
            result = engine.feel_frequency(args.freq, synthesize_audio=audio,
                                           render_fractal=fractal)
        elif args.va:
            v, a = args.va
            print(f"  Feeling valence={v:+.2f} arousal={a:.2f}...")
            result = engine.feel_valence_arousal(v, a, synthesize_audio=audio,
                                                  render_fractal=fractal)
        else:
            emotion_name = args.emotion or "Joy"
            print(f"  Feeling: {emotion_name}")
            result = engine.feel(emotion_name, synthesize_audio=audio,
                                 render_fractal=fractal)

        print(result.report())

    except ValueError as e:
        print(f"\n  Error: {e}\n")
        sys.exit(1)


def print_emotion_table():
    """Print all mapped emotions in a table."""
    emotions = get_all_emotions()
    emotions_sorted = sorted(emotions, key=lambda e: (e.valence, e.arousal))

    print("\n" + "═"*90)
    print("  THE FEELING ENGINE — All Mapped Human Emotions")
    print("═"*90)
    header = f"  {'Emotion':<16} {'Color':<8} {'Solfeggio':>9} {'EEG Band':<10} {'Mode':<14} {'Val':>5} {'Aro':>5}"
    print(header)
    print("  " + "─"*85)
    for em in emotions_sorted:
        print(
            f"  {em.name:<16} #{em.hex_color:<7} {em.solfeggio_hz:>8.1f}Hz "
            f"{em.eeg_band:<10} {em.musical_mode:<14} {em.valence:>+5.2f} {em.arousal:>5.2f}"
        )
    print("═"*90)
    print(f"\n  Total: {len(emotions)} emotions mapped across color, sound, fractal, and physiological dimensions.")
    print()


if __name__ == "__main__":
    main()
