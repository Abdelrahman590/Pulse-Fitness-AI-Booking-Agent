"""
Pulse Fitness — Data Layer (Mock Database)

ده الـ "source of truth" اللي الـ agent هيتعامل معاه بعدين عن طريق tools.
مفيش أي LLM هنا خالص — ده منطق عمل عادي (business logic) زي أي backend حقيقي.
الهدف: نتأكد إن القواعد صح الأول (الأسعار، التعارض بين المواعيد، إلخ)
قبل ما نحط أي موديل فوقه.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# =====================================================================
# 1) الخدمات والأسعار
# =====================================================================
SERVICES = {
    "Open Gym": [
        {"duration": "يوم واحد", "price": 250},
        {"duration": "شهر", "price": 2000},
        {"duration": "3 شهور", "price": 5400},
        {"duration": "6 شهور", "price": 9500},
        {"duration": "سنة", "price": 15000},
    ],
    "Personal Training": [
        {"duration": "جلسة", "price": 500},
        {"duration": "8 جلسات", "price": 3600},
        {"duration": "12 جلسة", "price": 4800},
        {"duration": "20 جلسة", "price": 7500},
    ],
    "Yoga": [{"duration": "جلسة", "price": 250}],
    "HIIT": [{"duration": "جلسة", "price": 300}],
    "Boxing": [{"duration": "جلسة", "price": 300}],
    "Pilates": [{"duration": "جلسة", "price": 350}],
    "Zumba": [{"duration": "جلسة", "price": 200}],
    "Sauna": [{"duration": "جلسة", "price": 250}],
    "Sports Massage": [{"duration": "50 دقيقة", "price": 600}],
    "Body Assessment": [{"duration": "جلسة", "price": 300}],
}


# =====================================================================
# 2) المدربين وتخصصاتهم
# =====================================================================
TRAINERS = {
    "Ahmed Hassan": ["Strength Training", "Weight Loss", "Muscle Building", "Personal Training"],
    "Omar Khaled": ["HIIT", "Functional Training", "Cross Training"],
    "Mariam Ali": ["Yoga", "Pilates", "Mobility"],
    "Youssef Adel": ["Boxing", "Kickboxing", "Fitness"],
}


# =====================================================================
# 3) الباقات (Packages)
# =====================================================================
PACKAGES = {
    "Starter": {
        "includes": ["1 Month Open Gym", "8 Group Classes"],
        "price": 2500,
    },
    "Fitness": {
        "includes": ["3 Months Open Gym", "20 Group Classes", "Body Assessment"],
        "price": 6500,
    },
    "Premium": {
        "includes": ["6 Months Open Gym", "Unlimited Group Classes", "8 PT Sessions", "Body Assessment"],
        "price": 12500,
    },
    "Elite": {
        "includes": ["12 Months Open Gym", "Unlimited Group Classes", "20 PT Sessions", "2 Body Assessments"],
        "price": 22000,
    },
}


# =====================================================================
# 4) جدول الـ Group Classes (ثابت أسبوعيًا)
# =====================================================================
GROUP_CLASSES_SCHEDULE = {
    # Saturday / Monday / Wednesday
    "Saturday": [
        {"time": "08:00 AM", "class": "Yoga", "trainer": "Mariam Ali"},
        {"time": "10:00 AM", "class": "HIIT", "trainer": "Omar Khaled"},
        {"time": "05:00 PM", "class": "Pilates", "trainer": "Mariam Ali"},
        {"time": "06:00 PM", "class": "Boxing", "trainer": "Youssef Adel"},
        {"time": "07:00 PM", "class": "Functional", "trainer": "Omar Khaled"},
        {"time": "08:00 PM", "class": "Zumba", "trainer": "Mariam Ali"},
    ],
    "Sunday": [
        {"time": "09:00 AM", "class": "Functional", "trainer": "Omar Khaled"},
        {"time": "11:00 AM", "class": "Pilates", "trainer": "Mariam Ali"},
        {"time": "05:00 PM", "class": "Boxing", "trainer": "Youssef Adel"},
        {"time": "06:00 PM", "class": "HIIT", "trainer": "Omar Khaled"},
        {"time": "07:00 PM", "class": "Yoga", "trainer": "Mariam Ali"},
        {"time": "08:00 PM", "class": "Strength", "trainer": "Ahmed Hassan"},
    ],
}
GROUP_CLASSES_SCHEDULE["Monday"] = GROUP_CLASSES_SCHEDULE["Saturday"]
GROUP_CLASSES_SCHEDULE["Wednesday"] = GROUP_CLASSES_SCHEDULE["Saturday"]
GROUP_CLASSES_SCHEDULE["Tuesday"] = GROUP_CLASSES_SCHEDULE["Sunday"]
GROUP_CLASSES_SCHEDULE["Thursday"] = GROUP_CLASSES_SCHEDULE["Sunday"]
# ملحوظة: الجدول الأصلي معندوش Friday صراحةً — هنسيبها فاضية عشان تمثل
# "مفيش group classes يوم الجمعة" كحقيقة بيانات، مش تخمين من حد


# =====================================================================
# 5) الـ Slots — ده الجزء اللي بيتغيّر ديناميكيًا (حجوزات فعلية)
# =====================================================================
@dataclass
class Slot:
    trainer: str
    date: str       # "YYYY-MM-DD"
    time: str        # "18:00-19:00"
    service: str
    is_booked: bool = False
    customer_id: Optional[str] = None


class BookingSystem:
    """
    ده الجزء المسؤول عن كل حاجة ليها علاقة بالتوفر والحجز الفعلي.
    أي "قرار" بخصوص إمكانية الحجز بييجي من هنا فقط — مش من أي تخمين خارجي.
    """

    def __init__(self):
        self.slots: list[Slot] = []
        self._seed_demo_slots()

    def _seed_demo_slots(self):
        # نفس مثال الـ PT بتاع Ahmed Hassan اللي جالك، ليوم Monday القريب (2026)
        demo_day = "2026-09-14"
        pt_slots = [
            ("08:00-09:00", True), ("09:00-10:00", False), ("10:00-11:00", False),
            ("11:00-12:00", True), ("12:00-13:00", False), ("17:00-18:00", True),
            ("18:00-19:00", False), ("19:00-20:00", False), ("20:00-21:00", True),
        ]
        for time_slot, booked in pt_slots:
            self.slots.append(
                Slot(trainer="Ahmed Hassan", date=demo_day, time=time_slot,
                     service="Personal Training", is_booked=booked)
            )

    def get_available_slots(self, trainer: str, date: str) -> list[str]:
        return [
            s.time for s in self.slots
            if s.trainer == trainer and s.date == date and not s.is_booked
        ]

    def book_slot(self, trainer: str, date: str, time: str, service: str, customer_id: str) -> dict:
        """
        الفنكشن دي هي الـ hard constraint الحقيقية.
        مفيش أي كلام هنا اسمه "الموديل قرر إن الجمعة متاحة" —
        إما فيه Slot فعلي فاضي، أو مفيش، وخلاص.
        """
        matching = [
            s for s in self.slots
            if s.trainer == trainer and s.date == date and s.time == time
        ]

        if not matching:
            # مفيش slot أصلاً معرّف لليوم/الوقت ده — يبقى نعمل واحد جديد فاضي ونحجزه
            # (في نظام حقيقي هيبقى فيه working-hours logic بدل ده، لكن كـ demo كفاية)
            new_slot = Slot(trainer=trainer, date=date, time=time, service=service)
            self.slots.append(new_slot)
            matching = [new_slot]

        slot = matching[0]
        if slot.is_booked:
            return {
                "success": False,
                "reason": f"الموعد {time} يوم {date} مع {trainer} محجوز بالفعل.",
            }

        slot.is_booked = True
        slot.customer_id = customer_id
        return {
            "success": True,
            "booking": {
                "service": service, "trainer": trainer,
                "date": date, "time": time,
                "price": get_service_price(service),
            },
        }


def get_service_price(service_name: str, duration: Optional[str] = None) -> Optional[int]:
    options = SERVICES.get(service_name)
    if not options:
        return None
    if duration is None:
        return options[0]["price"]  # أرخص/أول خيار كـ default
    for opt in options:
        if opt["duration"] == duration:
            return opt["price"]
    return None


def get_trainers_for_specialty(specialty: str) -> list[str]:
    return [name for name, specialties in TRAINERS.items() if specialty in specialties]


booking_system = BookingSystem()


# =====================================================================
# اختبار سريع يدوي — نتأكد إن المنطق شغال صح قبل أي agent
# =====================================================================
if __name__ == "__main__":
    print("خدمات Personal Training:", SERVICES["Personal Training"])
    print("سعر Yoga:", get_service_price("Yoga"))
    print("مدربين HIIT:", get_trainers_for_specialty("HIIT"))

    print("\nSlots متاحة لـ Ahmed Hassan يوم 2026-09-14:")
    print(booking_system.get_available_slots("Ahmed Hassan", "2026-09-14"))

    print("\nمحاولة حجز 09:00-10:00 (متاح):")
    result = booking_system.book_slot("Ahmed Hassan", "2026-09-14", "09:00-10:00", "Personal Training", "cust_1")
    print(result)

    print("\nمحاولة حجز نفس الموعد تاني (المفروض يرفض):")
    result = booking_system.book_slot("Ahmed Hassan", "2026-09-14", "09:00-10:00", "Personal Training", "cust_2")
    print(result)

    print("\nGroup classes يوم Friday (مفروض تكون فاضية):")
    print(GROUP_CLASSES_SCHEDULE.get("Friday", "لا يوجد جدول لهذا اليوم"))
