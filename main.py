"""
GSA56-2425 / DM-J4310-2EC 모터 상태 읽기
Python 3.7 호환  |  PEAK CAN USB @ 1Mbps

[ 실측 확인된 값 ]
  - 모터 CAN_ID  : 0x03  (모터가 수신)
  - Master ID    : 0x04  (모터가 송신, 진단으로 확인)
  - 피드백 DLC   : 4     (매뉴얼 표기와 다름, 실측 기준)

[ 피드백 프레임 DLC=4 파싱 추정 ]
  D[0] = ID | (ERR << 4)     ← 매뉴얼 4.1 D[1] 와 동일 구조
  D[1] = POS[15:8]   또는 상위 상태
  D[2] = POS[7:0]    또는 하위 상태
  D[3] = 추가 상태 or 온도

  [00 02 00 00] 해석:
    D[0]=0x00 → motor_id=0, error=0 (정상Disabled)
    D[1]=0x02 → ?
    D[2]=0x00
    D[3]=0x00

매뉴얼 4.1 원문 피드백 표 (DLC=8 기준):
  D[0]=MST_ID, D[1]=ID|ERR<<4,
  D[2]=POS[15:8], D[3]=POS[7:0],
  D[4]=VEL[11:4], D[5]=VEL[3:0]|T[11:8],
  D[6]=T[7:0], D[7]=T_MOS
"""

import can
import time
from typing import Optional, List
from dataclasses import dataclass, field

# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────
MOTOR_CAN_ID = 0x03   # 모터 수신 ID
MASTER_ID    = 0x04   # 모터 송신 ID (진단으로 확인)

P_MAX =  12.5;  P_MIN = -12.5   # rad
V_MAX =  50.0;  V_MIN = -50.0   # rad/s
T_MAX =  10.0;  T_MIN = -10.0   # Nm

CAN_INTERFACE = "pcan"
CAN_CHANNEL   = "PCAN_USBBUS1"
CAN_BITRATE   = 1000000

ERROR_CODES = {
    0x0: "Disabled(정상)",
    0x1: "Enable(작동중)",
    0x8: "과전압",
    0x9: "저전압",
    0xA: "과전류",
    0xB: "MOS과열",
    0xC: "권선과열",
    0xD: "통신실패",
    0xE: "과부하",
}


# ──────────────────────────────────────────────
# 변환 함수
# ──────────────────────────────────────────────
def uint_to_float(x_int, x_min, x_max, bits):
    # type: (int, float, float, int) -> float
    span = x_max - x_min
    return float(x_int) * span / float((1 << bits) - 1) + x_min


def float_to_uint(x, x_min, x_max, bits):
    # type: (float, float, float, int) -> int
    x = max(x_min, min(x_max, x))
    span = x_max - x_min
    return int((x - x_min) * float((1 << bits) - 1) / span)


# ──────────────────────────────────────────────
# 피드백 파싱 (두 포맷 모두 시도)
# ──────────────────────────────────────────────
@dataclass
class MotorFeedback:
    motor_id:   int   = 0
    error:      int   = 0
    position:   float = 0.0   # rad
    velocity:   float = 0.0   # rad/s
    torque:     float = 0.0   # Nm
    temp_mos:   int   = 0
    temp_rotor: int   = 0
    raw:        bytes = field(default_factory=bytes)

    def error_str(self):
        return ERROR_CODES.get(self.error,
                               "알수없음(0x{:X})".format(self.error))

    def __str__(self):
        return (
            "[ID=0x{:02X}] {:<16} "
            "pos={:8.4f}rad  vel={:8.4f}rad/s  "
            "torq={:7.4f}Nm  MOS={}C  rot={}C"
        ).format(
            self.motor_id, self.error_str(),
            self.position, self.velocity,
            self.torque, self.temp_mos, self.temp_rotor,
        )


def parse_dlc8(d):
    # type: (bytes) -> MotorFeedback
    """매뉴얼 4.1 표준 포맷 (DLC=8)"""
    motor_id = d[0]
    error    = (d[1] >> 4) & 0x0F
    p_int    = (d[2] << 8) | d[3]
    v_int    = (d[4] << 4) | (d[5] >> 4)
    t_int    = ((d[5] & 0x0F) << 8) | d[6]
    t_mos    = d[7]
    t_rotor  = d[8] if len(d) > 8 else 0
    return MotorFeedback(
        motor_id   = motor_id,
        error      = error,
        position   = uint_to_float(p_int, P_MIN, P_MAX, 16),
        velocity   = uint_to_float(v_int, V_MIN, V_MAX, 12),
        torque     = uint_to_float(t_int, T_MIN, T_MAX, 12),
        temp_mos   = t_mos,
        temp_rotor = t_rotor,
        raw        = bytes(d),
    )


def parse_dlc4(d):
    # type: (bytes) -> MotorFeedback
    """
    DLC=4 실측 포맷 추정 파싱.
    [00 02 00 00] → D[0]=ID|ERR<<4, D[1..3] = 상태 바이트들

    두 가지 해석을 모두 시도하여 출력:
      해석A: D[0]에 motor_id/error 포함, 나머지 위치/속도 축약
      해석B: D[1]이 상태 플래그 (0x02 = Enabled?)
    """
    # 해석A: 매뉴얼 D[1] 구조를 D[0]으로 당긴 경우
    motor_id_a = d[0] & 0x0F
    error_a    = (d[0] >> 4) & 0x0F
    # D[1]=0x02 일 때 → ERR=0, ID=2  또는  status flag

    # 해석B: D[0]=motor_id, D[1]=status(0x02=Enable)
    motor_id_b = d[0]
    error_b    = d[1]          # 0x02 = Enable 상태?

    print("      DLC=4 raw=[{}]".format(
        " ".join("{:02X}".format(b) for b in d)))
    print("      해석A: motor_id=0x{:02X}  error=0x{:X}({})".format(
        motor_id_a, error_a, ERROR_CODES.get(error_a, "?")))
    print("      해석B: motor_id=0x{:02X}  status_byte=0x{:02X}".format(
        motor_id_b, error_b))

    # 일단 해석A 기준으로 반환
    return MotorFeedback(
        motor_id = motor_id_a,
        error    = error_a,
        raw      = bytes(d),
    )


def parse_feedback(msg):
    # type: (can.Message) -> Optional[MotorFeedback]
    if msg.arbitration_id != MASTER_ID:
        return None
    d = msg.data
    if len(d) >= 8:
        return parse_dlc8(d)
    elif len(d) == 4:
        return parse_dlc4(d)
    return None


# ──────────────────────────────────────────────
# 제어 프레임
# ──────────────────────────────────────────────
def build_enter_frame():
    return bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFC])

def build_exit_frame():
    return bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFD])

def build_clear_error_frame():
    return bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFB])

def build_mit_frame(p_des=0.0, v_des=0.0, kp=0.0, kd=0.0, t_ff=0.0):
    p_int  = float_to_uint(p_des, P_MIN, P_MAX, 16)
    v_int  = float_to_uint(v_des, V_MIN, V_MAX, 12)
    kp_int = float_to_uint(kp,   0.0, 500.0, 12)
    kd_int = float_to_uint(kd,   0.0,   5.0, 12)
    t_int  = float_to_uint(t_ff, T_MIN, T_MAX, 12)
    data = bytearray(8)
    data[0] =  p_int >> 8
    data[1] =  p_int & 0xFF
    data[2] =  v_int >> 4
    data[3] = ((v_int  & 0x0F) << 4) | (kp_int >> 8)
    data[4] =  kp_int & 0xFF
    data[5] =  kd_int >> 4
    data[6] = ((kd_int & 0x0F) << 4) | (t_int >> 8)
    data[7] =  t_int & 0xFF
    return bytes(data)


def send(bus, can_id, data):
    # type: (can.Bus, int, bytes) -> None
    bus.send(can.Message(
        arbitration_id=can_id,
        data=data,
        is_extended_id=False,
    ))


def recv_feedback(bus, timeout=0.5):
    # type: (can.Bus, float) -> Optional[MotorFeedback]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        msg = bus.recv(timeout=0.05)
        if msg is None:
            continue
        fb = parse_feedback(msg)
        if fb is not None:
            return fb
    return None


# ──────────────────────────────────────────────
# STEP A: DLC=4 [00 02 00 00] 상세 분석
# ──────────────────────────────────────────────
def analyze_dlc4(bus):
    # type: (can.Bus) -> None
    """
    에러 클리어 / Enter / Exit 각 단계에서
    DLC=4 프레임의 D[1] 값 변화를 추적.
    D[1] 이 0x01(Enable) / 0x00(Disable) 로 바뀌면
    매뉴얼 D[1]=ID|ERR<<4 구조 확인 가능.
    """
    print("\n" + "="*60)
    print("DLC=4 프레임 상태 변화 분석")
    print("="*60)

    def sample(label, n=5):
        # type: (str, int) -> None
        print("\n  [{}]".format(label))
        for i in range(n):
            msg = bus.recv(timeout=0.3)
            if msg and msg.arbitration_id == MASTER_ID:
                d = msg.data
                print("    D[0]=0x{:02X}  D[1]=0x{:02X}  D[2]=0x{:02X}  D[3]=0x{:02X}".format(
                    d[0], d[1], d[2], d[3]))
                break

    # 베이스라인
    sample("초기 상태 (Enter 전)")

    print("\n  Enter 송신 ...")
    send(bus, MOTOR_CAN_ID, build_enter_frame())
    time.sleep(0.05)
    sample("Enter 직후")

    print("\n  MIT 영령(kd=0.5) 3회 송신 ...")
    cmd = build_mit_frame(kd=0.5)
    for _ in range(3):
        send(bus, MOTOR_CAN_ID, cmd)
        time.sleep(0.05)
    sample("MIT 명령 후")

    print("\n  Exit 송신 ...")
    send(bus, MOTOR_CAN_ID, build_exit_frame())
    time.sleep(0.05)
    sample("Exit 후")

    print("""
  해석 기준:
    D[1] 변화 없음(0x02 고정) → 상태 플래그 (0x02 = Disabled or 별도 포맷)
    D[1] 0x02→0x12 변화      → ERR=1(Enable), motor_id=2  (매뉴얼 ID|ERR<<4)
    D[1] 0x02→0x01 변화      → 별도 status byte 구조
    """)


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
def main():
    print("="*60)
    print("GSA56 상태 읽기  (MASTER_ID=0x{:02X})".format(MASTER_ID))
    print("="*60)

    bus = can.Bus(
        interface=CAN_INTERFACE,
        channel=CAN_CHANNEL,
        bitrate=CAN_BITRATE,
    )

    try:
        print("\n[1] 에러 클리어")
        send(bus, MOTOR_CAN_ID, build_clear_error_frame())
        time.sleep(0.1)

        # DLC=4 상세 분석
        analyze_dlc4(bus)

        print("\n[2] Enter 후 피드백 5회 샘플링")
        send(bus, MOTOR_CAN_ID, build_enter_frame())
        time.sleep(0.1)

        cmd = build_mit_frame(kd=0.5)
        for i in range(5):
            send(bus, MOTOR_CAN_ID, cmd)
            fb = recv_feedback(bus, timeout=0.3)
            if fb is not None:
                print("  [{}] {}".format(i+1, fb))
            else:
                print("  [{}] 피드백 없음".format(i+1))
            time.sleep(0.05)

    finally:
        print("\n[3] Exit 송신")
        try:
            send(bus, MOTOR_CAN_ID, build_exit_frame())
            time.sleep(0.1)
        except Exception:
            pass
        bus.shutdown()
        print("버스 종료.")


if __name__ == "__main__":
    main()