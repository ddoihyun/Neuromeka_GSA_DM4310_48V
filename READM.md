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
              PEAK CAN USB Adapter
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
python -m test.connection_test
```

## 🚀 실행