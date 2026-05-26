import pandas as pd
from collections import defaultdict
import os

# Vidusskolas klašu sadalīšana programmu virzienos
def separate_classes(df):
    classes = sorted(df["class"].unique())
    C = set()

    for c in classes:
        parts = c.split(".")
        grade, letter = parts[0], parts[1]
        if int(grade) >= 10:
            if letter == "a":
                C.add(f"{c}-HUM")
                C.add(f"{c}-UZN")
            elif letter == "b":
                C.add(f"{c}-MAT")
                C.add(f"{c}-DAB")
        else:
            C.add(c)
    return sorted(C)

def load_data():
    this_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(this_dir, "..", "data")

    # Ievaddatu ielāde no CSV failiem
    teacher_classes_df = pd.read_csv(os.path.join(data_dir, "teacher_classes.csv"))
    rooms_df = pd.read_csv(os.path.join(data_dir, "rooms.csv"))
    subjects_df = pd.read_csv(os.path.join(data_dir, "subjects.csv"))
    periods_df = pd.read_csv(os.path.join(data_dir, "periods.csv"))
    partition_options_df = pd.read_csv(os.path.join(data_dir, "shared_partition_options.csv"))
    
    T = sorted(teacher_classes_df["teacher_id"].unique().tolist())
    C = separate_classes(teacher_classes_df)
    R = sorted(rooms_df["room_id"].unique().tolist())
    S = sorted(subjects_df["subject"].unique().tolist())
    P = sorted(periods_df["period"].unique().tolist())
    D = [1, 2, 3, 4, 5]

    # Vienādu priekšmetu grupas ar dažādiem nosaukumiem
    SUBJECT_GROUPS = [
        {"Latviešu valoda", "Latviešu valoda un literatūra", "Latviešu literatūra", "Literatūra", "Latviešu valoda un literatūra I"},
        {"Sociālās zinības un vēsture", "Vēsture"},
        {"Sports un veselība", "Sports un veselība (praktiskā)", "Sports un veselība (teorija)"},
        {"Svešvaloda (angļu) I B2", "Svešvaloda (angļu) II C1", "Angļu valoda"},
        {"Angļu un amerikāņu literatūra", "Angļu literatūra"},
        {"Svešvaloda (otrā, vācu) I B1", "Svešvaloda (otrā, vācu) II B2", "Svešvaloda (vācu) I B1", "Vācu valoda", "Vācu valoda akadēmiskiem nolūkiem"},
        {"Mazākumtautību valoda un literatūra", "Krievu valoda un literatūra"}
    ]
    PROGRAM_MAPPING = {
        "HUM": "Humanitārās zinātnes un kultūra",
        "UZN": "Uzņēmējdarbības pamati",
        "MAT": "Matemātika, dabaszinātnes un tehnoloģijas",
        "DAB": "Dabaszinātnes"
    }

    # Koplietoto priekšmetu sadalījuma variantu ielāde
    partition_variants = {}
    partition_streams = defaultdict(list)
    for key, group in partition_options_df.groupby("partition_key"):
        variants = sorted(group["variant_id"].unique())
        partition_variants[key] = variants
        for _, stream_row in group.iterrows():
            codes = str(stream_row["participant_suffixes"]).split(";")
            codes = tuple(s for s in codes if s)
            
            # Viena varianta viena plūsma un tajā iekļautās programmas
            partition_streams[key].append((
                str(stream_row["variant_id"]),
                int(stream_row["stream_id"]),
                codes
            ))

    classes_grade = defaultdict(list)
    for c in C:
        classes_grade[int(c.split(".")[0])].append(c)
    for grade in classes_grade:
        classes_grade[grade] = sorted(classes_grade[grade])

    # Programmas koda iegūšana no klases nosaukuma
    def class_code(c):
        parts = c.split("-")
        if len(parts) > 1:
            return parts[1]
        return ""

    # Klašu kopu noteikšana koplietotajiem priekšmetiem
    def groups_options(c_sep, sh_key, share_mode):
        grade = int(c_sep.split(".")[0])

        # Visi vienas paralēles skolēni apmeklē priekšmetu vienlaikus
        if share_mode == "forced_parallel_groups" and sh_key:
            return [(tuple(classes_grade[grade]), 0, "")]

        # Modelis vēlāk izvēlas vienu no iespējamiem programmu sadalījumiem
        if share_mode == "fixed_pair_partition" and sh_key in partition_streams:
            code = class_code(c_sep)
            options = []
            for variant_id, stream_id, codes in partition_streams[sh_key]:
                if code in codes:
                    participants = [c for c in classes_grade[grade] if class_code(c) in codes]
                    options.append((tuple(sorted(participants)), stream_id, variant_id))
            if options:
                return options
            
        return [((c_sep,), 0, "")]

    def subject_in_group(subject_name, group):
        subject_name = str(subject_name)
        return any(
            subject_name == group_subject or subject_name.startswith(group_subject + " ")
            for group_subject in group
        )

    L = []
    Req = defaultdict(int)
    Qual = defaultdict(int)
    Lessons = []
    Participants = {}
    ShareMode = {}
    GroupIndex = {}
    Instance = {}
    StreamId = {}
    SyncKey = {}
    PartitionKey = {}
    VariantId = {}

    # Potenciālo nodarbību ierakstu izveide
    for _, row in teacher_classes_df.iterrows():
        t = row["teacher_id"]   
        s = row["subject"]    
        c_orig = row["class"]
        grade = int(c_orig.split(".")[0])
        
        for c_sep in C:
            if c_sep.startswith(c_orig):
                # Atrod konkrētās klases mācību plānu
                grade_curriculum = subjects_df[subjects_df["grade"] == grade]
                if int(grade) >= 10:
                    parts = c_sep.split("-")
                    if len(parts) > 1:
                        code = parts[1]
                        current_program = PROGRAM_MAPPING.get(code)
                        if current_program:
                            grade_curriculum = grade_curriculum[grade_curriculum["program"] == current_program]

                # Meklē līdzvērtīgu priekšmetu grupu
                matched_group = None
                for group in SUBJECT_GROUPS:
                    if s in group:
                        matched_group = group
                        break
                
                if matched_group:
                    condition = grade_curriculum["subject"].apply(lambda subject_name: subject_in_group(subject_name, matched_group))
                else:
                    condition = (grade_curriculum["subject"] == s) | (grade_curriculum["subject"].str.startswith(s + " ", na=False))
                match = grade_curriculum[condition]

                if match.empty:
                    continue

                # Vienam skolotāja-priekšmeta ierakstam var atbilst vairāki mācību plāna ieraksti
                for _, match_row in match.iterrows():
                    subject = match_row["subject"] 
                    lessons_per_week = int(match_row["lessons_per_week"])
                    g_count = int(match_row["group_count"])
                    sh_key = match_row["shared_group_key"]
                    share_mode = match_row.get("share_mode", "none")
                    
                    if pd.isna(sh_key): 
                        sh_key = ""
                    if pd.isna(share_mode):
                        share_mode = "none"

                    Req[(c_sep, subject)] = lessons_per_week
                    Qual[(t, subject)] = 1

                    # Izveido nodarbības dalībniekus, ņemot vērā koplietošanas režīmu
                    for participants, stream_id, variant_id in groups_options(c_sep, sh_key, share_mode):
                        Lessons.append({
                            "class": c_sep,
                            "participants": participants,
                            "subject": subject,
                            "shared_key": sh_key,
                            "share_mode": share_mode,
                            "teacher": t,
                            "lessons_per_week": lessons_per_week,
                            "group_count": g_count,
                            "stream_id": stream_id,
                            "variant_id": variant_id,
                        })

    # Vienādu koplietoto nodarbību apvienošana
    grouped_lessons = {}
    for lesson in Lessons:
        if lesson["share_mode"] == "forced_parallel_groups":
            key = ("forced", lesson["shared_key"])
        else:
            key = (
                "normal",
                lesson["participants"],
                lesson["subject"],
                lesson["shared_key"],
                lesson["share_mode"],
                lesson["stream_id"],
                lesson["variant_id"],
            )
        item = grouped_lessons.setdefault(key, {
            "participants": lesson["participants"],
            "subject": lesson["subject"],
            "shared_key": lesson["shared_key"],
            "share_mode": lesson["share_mode"],
            "stream_id": lesson["stream_id"],
            "variant_id": lesson["variant_id"],
            "lessons_per_week": lesson["lessons_per_week"],
            "group_count": lesson["group_count"],
            "teachers": set(),
        })
        item["teachers"].add(lesson["teacher"])
        item["lessons_per_week"] = max(item["lessons_per_week"], lesson["lessons_per_week"])
        item["group_count"] = max(item["group_count"], lesson["group_count"])

    # Nodarbību identifikatoru izveide modelim
    for item in grouped_lessons.values():
        participants = tuple(sorted(item["participants"]))
        primary_class = participants[0]
        subject = item["subject"]
        sh_key = item["shared_key"]
        share_mode = item["share_mode"]
        stream_id = item["stream_id"]
        variant_id = item["variant_id"]
        lessons_per_week = item["lessons_per_week"]
        g_count = item["group_count"]
        teachers = sorted(item["teachers"])

        if not teachers:
            continue
        
        # Grupu skaits nevar pārsniegt pieejamo skolotāju skaitu
        if share_mode == "forced_parallel_groups":
            g_count = min(g_count, len(teachers))

        participants_label = "+".join(participants)
        for g in range(1, g_count + 1):
            # Skolotāji tiek sadalīti pa grupām cikliski
            teacher = teachers[(g - 1) % len(teachers)]
            for i in range(1, lessons_per_week + 1):
                lesson_id = f"{participants_label}_{subject}_{teacher}_g---------------r{g}_ins{i}"
                if stream_id:
                    lesson_id = f"{participants_label}_{subject}_stream{stream_id}_{teacher}_gr{g}_ins{i}"
                if variant_id:
                    lesson_id = f"{variant_id}_{lesson_id}"
                L.append((
                    lesson_id,
                    primary_class,
                    subject,
                    sh_key,
                    teacher,
                    g_count
                ))
                Participants[lesson_id] = participants
                ShareMode[lesson_id] = share_mode
                GroupIndex[lesson_id] = g
                Instance[lesson_id] = i
                StreamId[lesson_id] = stream_id
                PartitionKey[lesson_id] = sh_key if variant_id else ""
                VariantId[lesson_id] = variant_id
                if share_mode == "forced_parallel_groups" and sh_key:
                    # Šī atslēga vēlāk sinhronizē vienas nodarbības paralēlās grupas
                    SyncKey[lesson_id] = f"{sh_key}_ins{i}"
                else:
                    SyncKey[lesson_id] = ""

    L = sorted(list(set(L)))

    # Kabinetu piemērotības un ēkas atbilstības noteikšana
    Fit = defaultdict(int)
    Suit = defaultdict(int)
    room_types = dict(zip(rooms_df["room_id"], rooms_df["type"]))
    room_capacities = dict(zip(rooms_df["room_id"], rooms_df["capacity"]))

    for r in R:
        r_type = room_types.get(r, "classroom")
        r_cap = room_capacities.get(r, 30)
        for l in L:
            l_id = l[0]
            l_class = l[1]
            l_subj = l[2]
            l_grade = int(l_class.split(".")[0])

            if l_grade <= 5 and r.startswith("A-"):
                Suit[(r, l_id)] = 1
            elif l_grade >= 6 and r.startswith("T-"):
                Suit[(r, l_id)] = 1
            else:
                Suit[(r, l_id)] = 0

            # Aptuvenais skolēnu skaits vienā grupā
            l_g_count = l[5]
            l_sh_key = l[3]
            if l_grade >= 10:
                if l_sh_key != "":
                    num_combined_groups = len(Participants.get(l_id, (l_class,)))
                    total_students = 15 * num_combined_groups           
                    estimated_students = total_students // l_g_count
                else:
                    estimated_students = 15
            else:
                if l_g_count > 1:
                    estimated_students = 15
                else:
                    estimated_students = 30
            if r_cap < estimated_students:
                Fit[(r, l_id)] = 0
                continue

            # Kabineta tipa atbilstība priekšmetam
            if l_subj in ["Sports un veselība", "Sports un veselība (praktiskā)"] and r_type == "sport": 
                Fit[(r, l_id)] = 1
            elif l_subj == "Sports un veselība (teorija)" and r_type == "classroom":
                Fit[(r, l_id)] = 1
            elif l_subj in ["Datorika", "Programmēšana I", "Programmēšana II"] and r_type == "computer": 
                Fit[(r, l_id)] = 1
            elif l_subj in ["Ķīmija", "Ķīmija I", "Ķīmija II"] and r_type == "chemistry": 
                Fit[(r, l_id)] = 1
            elif (l_subj != "Sports un veselība (praktiskā)" and l_subj != "Sports un veselība (teorija)" and 
                  l_subj not in ["Datorika", "Programmēšana I", "Programmēšana II", "Ķīmija", "Ķīmija I", "Ķīmija II"] and 
                  r_type == "classroom"):                
                Fit[(r, l_id)] = 1
            else:
                Fit[(r, l_id)] = 0

    # Maksimālais paralēlo grupu skaits klasei un priekšmetam
    MaxGroup = defaultdict(int)
    for c in C:
        grade = int(c.split(".")[0])
        for s in S:
            match = subjects_df[(subjects_df["grade"] == grade) & (subjects_df["subject"] == s)]
            if not match.empty:
                MaxGroup[(c, s)] = int(match.iloc[0]["group_count"])
            else:
                MaxGroup[(c, s)] = 1

    # Skolotāju pieejamības dati
    availability_df = pd.read_csv(os.path.join(data_dir, "teacher_availability.csv"))
    Avail = {}
    for _, row in availability_df.iterrows():
        Avail[(row["teacher_id"], int(row["day"]), int(row["period"]))] = int(row["available"])

    # Skolotājiem nevēlamie laiki
    unfavorable_df = pd.read_csv(os.path.join(data_dir, "teacher_unfavorable.csv"))
    Unf = {}
    for _, row in unfavorable_df.iterrows():
        Unf[(row["teacher_id"], int(row["day"]), int(row["period"]))] = int(row["unfavorable"])

    # Skolotāju dienas slodzes robežas
    teacher_load_df = pd.read_csv(os.path.join(data_dir, "teacher_load.csv"))
    MaxDay, MinDay = {}, {}
    for _, row in teacher_load_df.iterrows():
        t = row["teacher_id"]
        MaxDay[t] = int(row["max_day"])
        MinDay[t] = int(row["min_day"])

    # Klašu dienas parametri
    class_params_df = pd.read_csv(os.path.join(data_dir, "class_params.csv"))
    MaxPerDay, MinStart = {}, {}
    for _, row in class_params_df.iterrows():
        c_orig = row["class"]
        for c_sep in C:
            if c_sep.startswith(c_orig):
                MaxPerDay[c_sep] = int(row["max_per_day"])
                MinStart[c_sep] = int(row["min_start"])

    # Visi modelim nepieciešamie dati
    return {
        "T": T, "C": C, "R": R, "S": S, "P": P, "D": D, "L": L,
        "Avail": Avail, "Req": dict(Req), "Qual": dict(Qual), "Fit": dict(Fit), "Suit": dict(Suit), "Unf": Unf,
        "Participants": Participants, "ShareMode": ShareMode, "GroupIndex": GroupIndex,
        "Instance": Instance, "StreamId": StreamId, "SyncKey": SyncKey,
        "PartitionKey": PartitionKey, "VariantId": VariantId,
        "PartitionVariants": partition_variants,
        "MaxDay": MaxDay, "MinDay": MinDay, 
        "MaxPerDay": MaxPerDay, "MinStart": MinStart, "MaxGroup": dict(MaxGroup)
    }
