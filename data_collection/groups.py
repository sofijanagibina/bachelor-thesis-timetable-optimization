import pandas as pd

df = pd.read_csv("data/subjects.csv")

# Programmu īsie kodi
PROGRAM_CODES = {
    "Humanitārās zinātnes un kultūra": "HUM",
    "Uzņēmējdarbības pamati": "UZN",
    "Matemātika, dabaszinātnes un tehnoloģijas": "MAT",
    "Dabaszinātnes": "DAB",
}

# Noklusētais grupu skaits konkrētiem priekšmetiem
BASE_GROUPS = {
    "Angļu valoda": 2,
    "Latviešu valoda": 2,
    "Datorika": 2,
    "Vācu valoda": 2,
}

# Vācu valodas priekšmetu nosaukumi, kas tiek apvienoti vienā grupā
GERMAN = [
    "Svešvaloda (otrā, vācu) I B1",
    "Svešvaloda (vācu) I B1",
]

# Īsie kodi koplietoto priekšmetu atslēgām
SUBJECT_CODES = {
    "Bioloģija I": "BIO",
    "Bioloģija II": "BIO",
    "Ekonomika": "ECON",
    "Fizika I": "PHYS",
    "Fizika II": "PHYS",
    "Kultūras pamati": "CULT",
    "Latviešu valoda un literatūra I": "LAT",
    "Matemātika I": "MATH",
    "Matemātika II": "MATH",
    "Mazākumtautību valoda un literatūra": "RUS",
    "Sociālās zinības un vēsture": "SOC",
    "Sociālās zinātnes un vēsture I": "SOC",
    "Sports un veselība (teorija)": "SPORTT",
    "Svešvaloda (angļu) I B2": "ENG",
    "Svešvaloda (angļu) II C1": "ENG2",
    "Svešvaloda (otrā, vācu) II B2": "GERMAN2",
    "Uzņemējdarbības pamati": "UZN",
    "Vācu valoda akadēmiskiem nolūkiem": "GERMANAK",
    "Ģeogrāfija I": "GEO",
    "Ģeogrāfija II": "GEO",
    "Ķīmija I": "CHEM",
    "Ķīmija II": "CHEM",
}

# Programmas nosaukuma pārveidošana īsajā kodā
def code(program):
    if pd.isna(program):
        return ""
    return PROGRAM_CODES.get(program, str(program).replace(" ", "_"))

# Pārbauda, vai klase ir vidusskolas posmā
def is_senior(grade):
    return 10 <= int(grade) <= 12

# Sporta priekšmetu noteikšana
def is_sport(subject):
    return subject in ["Sports un veselība", "Sports un veselība (praktiskā)"]

# Grupu skaita noteikšana priekšmetam
def get_group_count(row):
    subject = row["subject"]
    grade = int(row["grade"])

    if subject == "Literatūra" and grade == 4:
        return 2
    if subject == "Datorika" and grade == 10:
        return 1
    if subject in GERMAN and is_senior(grade):
        return 4
    return BASE_GROUPS.get(subject, 1)

# Koplietotās grupas atslēgas veidošana
def get_shared_key(row):
    subject = row["subject"]
    grade = int(row["grade"])

    if is_sport(subject):
        if 6 <= grade <= 9:
            return f"SPORT_{grade}"
        if is_senior(grade):
            return f"SPORT_{grade}_ALL"
    if subject in GERMAN and is_senior(grade):
        return f"GERMAN_{grade}_ALL"
    programs = programs_for_subject.get((grade, subject), set())
    if is_senior(grade) and len(programs) >= 2:
        pref = SUBJECT_CODES.get(subject, subject.upper().replace(" ", "_"))
        return f"{pref}_{grade}"
    return ""

# Koplietošanas tipa noteikšana
def get_share_mode(row):
    subject = row["subject"]
    grade = int(row["grade"])
    key = row["shared_group_key"]

    if not key:
        return "none"
    if is_sport(subject) and 6 <= grade <= 9:
        return "optional_single_or_pair"
    if is_senior(grade) and (is_sport(subject) or subject in GERMAN):
        return "forced_parallel_groups"
    if is_senior(grade):
        return "fixed_pair_partition"
    return "none"

# Iespējamo programmu sadalījumu izveide pāru priekšmetiem
def make_pair_variants(programs):
    programs = sorted(programs)
    if len(programs) == 2:
        return [[tuple(programs)]]
    if len(programs) == 3:
        a, b, c = programs
        return [
            [(a, b), (c,)],
            [(a, c), (b,)],
            [(b, c), (a,)],
        ]
    if len(programs) == 4:
        a, b, c, d = programs
        return [
            [(a, b), (c, d)],
            [(a, c), (b, d)],
            [(a, d), (b, c)],
        ]
    result = []
    current = []
    for p in programs:
        current.append((p,))
    result.append(current)
    return result

# Programmu kopas izveide katram priekšmetam un klasei
programs_for_subject = {}
for _, row in df.iterrows():
    grade = int(row["grade"])
    subject = row["subject"]
    program = code(row["program"])
    if is_senior(grade) and program:
        programs_for_subject.setdefault((grade, subject), set()).add(program)

# Grupu un koplietošanas lauku pievienošana priekšmetiem
df["group_count"] = df.apply(get_group_count, axis=1)
df["shared_group_key"] = df.apply(get_shared_key, axis=1)
df["share_mode"] = df.apply(get_share_mode, axis=1)

# Sadalījumu variantu sagatavošana koplietotajiem priekšmetiem
partition_rows = []
pairs_df = df[df["share_mode"] == "fixed_pair_partition"]
for key, group in pairs_df.groupby("shared_group_key"):
    programs = set()
    for program in group["program"]:
        programs.add(code(program))
    variants = make_pair_variants(programs)
    for v_idx, variant in enumerate(variants, start=1):
        for stream_idx, stream in enumerate(variant, start=1):
            partition_rows.append({
                "partition_key": key,
                "variant_id": f"v{v_idx}",
                "stream_id": stream_idx,
                "participant_suffixes": ";".join(stream),
            })
            
partition_options = pd.DataFrame(
    partition_rows,
    columns=[
        "partition_key",
        "variant_id",
        "stream_id",
        "participant_suffixes",
    ],
)

# Gala priekšmetu tabulas sagatavošana
df = df[[
    "grade",
    "program",
    "subject",
    "lessons_per_week",
    "optional",
    "group_count",
    "shared_group_key",
    "share_mode",
]]

# Rezultātu saglabāšana CSV failos
df.to_csv("data/subjects.csv", index=False, encoding="utf-8")
partition_options.to_csv("data/shared_partition_options.csv", index=False, encoding="utf-8")
