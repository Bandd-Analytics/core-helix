# VectorBT Pro — Licensing & Sponsorship Notes

Access to VectorBT Pro is gated behind a **GitHub Sponsors subscription** to
[polakowo](https://github.com/polakowo). The full source (839MB) and offline
documentation (83MB) live at `V2/vbt/` (gitignored — not committed to this repo).

---

## What the license allows (non-commercial use)

- Personal/private trading on your own account — allowed
- Internal R&D, backtesting, strategy development — allowed
- Modifying the source for private use — allowed

## What requires a separate commercial license

- Offering Helix as a service or product to others
- Any use where third parties pay for outcomes derived from VBT
- Contact Oleg Polakow directly if this ever applies

---

## If the sponsorship lapses

**Technically:** Nothing breaks. There is no phone-home check, no activation key,
no expiry timer in the runtime. Once installed (`pip install -e V2/vbt/main/`),
it runs offline indefinitely.

**Legally:** License Section 5.1 says you must "immediately cease all use and
permanently delete all copies" upon termination. The library keeps working but
you are no longer licensed to use it.

**Practically:** Keep the sponsorship active while actively developing against it
— you need the private GitHub repo to pull updates. If access lapses, nothing
breaks immediately, but do not continue using it in production.

## What you lose if access lapses

- Pull access to the private GitHub repo (no new versions)
- Access to the private Discord server
- The local `V2/vbt/` clone technically becomes an unlicensed copy

---

## Installing

VBT Pro is **not installed by default** — cloning the source is not enough.
Python's import system only finds packages registered in site-packages.
The editable install creates that registration without copying files:

```bash
pip install -e V2/vbt/main/
```

Run this once. After that `import vectorbtpro` works from anywhere in the project.
To verify: `python3 -c "import vectorbtpro; print(vectorbtpro.__version__)"`.

---

*Note recorded: 2026-04-24*
