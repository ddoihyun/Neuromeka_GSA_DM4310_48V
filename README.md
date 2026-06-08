# DM4310 CAN Control System (Python + PEAK CAN)
📌 개요
본 프로젝트는 Python을 이용하여 PEAK CAN USB Adapter를 통해
GSA DM4310 모터 드라이버(CAN 통신)를 제어 및 테스트하는 시스템입니다.

## 🧱 하드웨어 구성
```
220V AC → SMPS → DC 24V
                    ↓
              GSA DM4310 (전원 + CAN H/L)
                    ↑
              PEAK CAN USB Adapter 또는 DM Tools (USB2CAN)
                    ↑
                 Laptop (Python)
```

## ⚙️ Python 환경 설정
Step1 - venv라는 이름의 가상환경 생성
```
python -m venv venv
```

Step2 - Windows에서 가상환경 활성화
```
venv\Scripts\activate
```

Step3 - pip 최신 버전으로 업데이트
```
pip install --upgrade pip
```

Step4 - 프로젝트 의존성 설치
```
pip install -r requirements.txt
```

## 🧪 연결 테스트
가상환경 활성화 후:
```
python -m tests.connection_test
```

실행 예시:
```
============================================================
CAN Devices
============================================================
[1]
  interface: pcan
  channel: PCAN_USBBUS1
  supports_fd: False
  controller_number: 0
  device_features: 0
  device_id: 255
  device_name: PCAN-USB
  device_type: 5
  channel_condition: 1

============================================================
Serial Ports
============================================================
시리얼 포트를 찾을 수 없습니다.
```

```
============================================================
CAN Devices
============================================================
PCAN 장치를 찾을 수 없습니다.

============================================================
Serial Ports
============================================================
[1]
  Device      : COM4
  Description : USB 직렬 장치(COM4)
  HWID        : USB VID:PID=2E88:4603 SER=00000000050C
  VID         : 0x2e88
  PID         : 0x4603
```


## 🚀 실행