"""
/style on the owner's Job Hunt bot (owner request 2026-11-22): copy-and-paste AI prompts for
MummyTKT Style House pictures and twirl videos. Each prompt is a <code> box: one tap copies it.

The fixed parts (studio, sign, lighting, framing) are the same text in every prompt, so the
"shop" looks identical across all styles. Outfit lines are swapped into [OUTFIT].
"""

from __future__ import annotations

import html

STUDIO = ("Setting: a luxury Nigerian kids' and family fashion boutique studio with cream walls and soft gold "
          "panel moulding, a polished cream marble floor, a tall arrangement of cream roses in a gold vase on the "
          "left, a plush cream pouf on the right. On the back wall, a large elegant gold sign in serif lettering "
          "that reads \"MummyTKT\", with the smaller words \"STYLE HOUSE\" underneath.")
LOOK = ("Vertical 4:5, full body head to toe, shoes visible, model centred, soft warm studio lighting, sharp fabric "
        "detail, photorealistic, like a Nigerian fashion boutique advert on Instagram.")

PROMPTS = [
    ("1️⃣ First picture (sets your shop)", "Use once, until you get a picture you love. Replace [OUTFIT].",
     f"{LOOK}\n[OUTFIT]\n{STUDIO}"),
    ("2️⃣ Same shop, new outfit", "Upload your favourite picture first. Keeps the studio and sign identical.",
     "Use the exact same background, sign, flowers, floor, lighting and camera angle as this image. "
     "Replace only the model and outfit with: [OUTFIT]\nKeep the sign reading exactly \"MummyTKT\" with "
     "\"STYLE HOUSE\" underneath. Photorealistic, full body, shoes visible."),
    ("3️⃣ Same model, new outfit", "Upload a picture of the child/model you want to keep.",
     "Keep the same model (same face, hair, skin tone, age and pose), the same background, sign and lighting. "
     "Change only the outfit to: [OUTFIT]\nPhotorealistic, full body, shoes visible."),
    ("4️⃣ One small change", "Upload your picture. ONE change per message, or Gemini redraws everything.",
     "Keep everything exactly the same: the model, her face, pose, hair, outfit, background, sign and "
     "lighting. Only change this one thing: [CHANGE]"),
    ("5️⃣ Use someone's photo as a style guide", "Upload the inspiration photo. Copies the feel, not her design.",
     f"Use this photo only as a style reference. Create a NEW photo with the same look: same camera angle, "
     f"full-body pose, soft boutique lighting, realistic skin and fabric detail, same level of luxury.\n"
     f"Change the outfit to: [OUTFIT]\n{STUDIO}\nDo not copy the original sign or the original outfit exactly."),
    ("6️⃣ Fix the sign", "When the sign comes out misspelled.",
     "Keep everything else exactly the same. Fix only the sign on the back wall: it must read exactly "
     "\"MummyTKT\" in gold serif letters, with \"STYLE HOUSE\" smaller underneath."),
]

VIDEOS = [
    ("👗 Girls / dresses",
     "Keep the face, outfit and background exactly the same. The girl does a slow, graceful twirl so the skirt "
     "flares out, then turns to show the back of the dress, then faces the camera and smiles. Static camera, "
     "smooth natural motion, 5 seconds."),
    ("🤵 Boys and men",
     "Keep the face, outfit and background exactly the same. He walks two steps toward the camera with "
     "confidence, turns slowly to show the back and side of the outfit, then faces forward and adjusts his cap. "
     "Static camera, smooth natural motion, 5 seconds."),
    ("💃 Women",
     "Keep the face, outfit and background exactly the same. She walks toward the camera like a runway model, "
     "turns slowly to show the back of the gown, then poses with one hand on her waist. Static camera, smooth "
     "natural motion, 5 seconds."),
]

OUTFITS = [
    ("Owambe lace ball gown (girl)",
     "a 5-year-old Nigerian girl in an owambe party ball gown: fitted bodice of beaded cord lace with sparkling "
     "stones, off-shoulder puff sleeves, a very full floor-length skirt of layered tulle, a matching lace hair band "
     "with stones, a small pearl purse, like Lagos children's party wear"),
    ("Ankara & tulle party dress (girl)",
     "a 6-year-old Nigerian girl in an ankara party dress: ankara print bodice with ruffled cap sleeves, a tiered "
     "ankara skirt over a fluffy white tulle petticoat, a matching ankara bow headband, gold sandals"),
    ("Aso-ebi with mini gele (girl)",
     "a 7-year-old Nigerian girl in an aso-ebi outfit: a gold beaded lace gown with a peplum waist and a mermaid "
     "flare, a matching mini gele tied on her head, gold shoes, owambe style"),
    ("Sequin birthday princess (girl)",
     "a 5-year-old Nigerian girl in a birthday princess gown: a silver sequin bodice, a big pink layered tulle "
     "skirt with ruffles at the hem, puff sleeves, a crown tiara"),
    ("Satin church dress (girl)",
     "a 5-year-old Nigerian girl in an emerald green satin church dress with a fitted bodice, wide square "
     "neckline, full knee-length skirt with a tulle underlayer, a matching satin bow in her curly hair, white "
     "socks and black patent shoes"),
    ("Mini agbada (boy)",
     "a 6-year-old Nigerian boy in a navy blue mini agbada set with gold embroidery on the chest, matching "
     "trousers and a fila cap, brown leather loafers, standing proudly"),
    ("Ankara shirt & bow tie (boy)",
     "a 5-year-old Nigerian boy in a short-sleeved ankara shirt in green and gold print, cream chinos, a matching "
     "ankara bow tie, white sneakers"),
    ("Ankara wrap gown (woman)",
     "a Nigerian woman in her thirties in a floor-length ankara wrap gown with dramatic puff sleeves and a "
     "thigh-high front slit, purple and gold print, a gele head tie, gold heels"),
    ("Senator kaftan (man)",
     "a Nigerian man in his thirties in a wine-red senator kaftan with subtle tone-on-tone embroidery down the "
     "front, matching trousers, a black cap, black loafers"),
    ("Mother & daughter matching",
     "a Nigerian mother and her 6-year-old daughter in matching ankara outfits: the mother in a mermaid gown, the "
     "daughter in a flared knee-length dress, both in the same teal and coral print, holding hands"),
]

CHANGES = ["make the dress wine red", "add long puff sleeves", "make the skirt floor-length",
           "add sparkling stones on the bodice", "change the fabric to gold beaded lace",
           "add a matching mini gele", "make her 3 years old", "change the shoes to gold sandals"]


def _box(text: str) -> str:
    return f"<code>{html.escape(text, quote=False)}</code>"


def messages() -> list[str]:
    """The /style answer, split so each message stays well under Telegram's 4096-character limit."""
    intro = ("🎨 <b>MummyTKT Style House: AI prompts</b>\nTap a grey box to copy it, paste into Gemini, then "
             "replace the [WORD IN BRACKETS].\n\nPictures: Gemini (or Whisk). Videos: Flow / Veo, Kling or "
             "TikTok AI Alive.")
    first = [intro] + [f"\n<b>{t}</b>\n<i>{html.escape(h)}</i>\n{_box(p)}" for t, h, p in PROMPTS[:3]]
    second = [f"<b>{t}</b>\n<i>{html.escape(h)}</i>\n{_box(p)}\n" for t, h, p in PROMPTS[3:]]
    second.append("<b>Ideas for [CHANGE]</b> (tap to copy one)\n" + "\n".join(_box(c) for c in CHANGES))
    outfits = ["👗 <b>Outfits for [OUTFIT]</b>\nCopy one and paste it in place of [OUTFIT].\n"] + \
              [f"<b>{html.escape(t)}</b>\n{_box(o)}\n" for t, o in OUTFITS]
    videos = ["🎬 <b>Make it move</b>\nUpload your final picture to Flow, Kling or TikTok AI Alive, then paste:\n"] + \
             [f"<b>{t}</b>\n{_box(v)}\n" for t, v in VIDEOS] + \
             ["<i>Keep TikTok's AI-generated label on, and call them \"style ideas\", never \"our work\".</i>"]
    return ["\n".join(first), "\n".join(second), "\n".join(outfits), "\n".join(videos)]
