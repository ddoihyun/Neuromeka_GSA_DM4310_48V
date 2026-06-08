import can
import serial
import serial.tools.list_ports


def list_can_devices():
    print("=" * 60)
    print("CAN Devices")
    print("=" * 60)

    try:
        configs = can.detect_available_configs(interfaces="pcan")

        if not configs:
            print("PCAN 장치를 찾을 수 없습니다.\n")
            return

        for idx, cfg in enumerate(configs, start=1):
            print(f"[{idx}]")
            for k, v in cfg.items():
                print(f"  {k}: {v}")
            print()

    except Exception as e:
        print("CAN 검색 실패:", e)


def list_serial_ports():
    print("=" * 60)
    print("Serial Ports")
    print("=" * 60)

    ports = serial.tools.list_ports.comports()

    if not ports:
        print("시리얼 포트를 찾을 수 없습니다.\n")
        return

    for idx, port in enumerate(ports, start=1):
        print(f"[{idx}]")
        print("  Device      :", port.device)
        print("  Description :", port.description)
        print("  HWID        :", port.hwid)

        if port.vid:
            print("  VID         :", hex(port.vid))

        if port.pid:
            print("  PID         :", hex(port.pid))

        print()


def test_serial_connection(port_name, baudrate=921600):
    """
    모터 UART 연결 확인
    """

    print(f"\n[TEST] {port_name} @ {baudrate}")

    try:
        with serial.Serial(
            port=port_name,
            baudrate=baudrate,
            timeout=1
        ) as ser:

            print("연결 성공")

            # 버퍼 비우기
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            # 수신 데이터 확인
            data = ser.read(64)

            if data:
                print("수신 데이터:")
                print(data.hex(" "))
            else:
                print("수신 데이터 없음")

            return True

    except Exception as e:
        print("연결 실패:", e)
        return False


if __name__ == "__main__":

    # 1. CAN 장치 검색
    list_can_devices()

    # 2. Serial 포트 검색
    list_serial_ports()

    # 3. 특정 포트 테스트 예시
    #
    # Windows:
    # test_serial_connection("COM5")
    #
    # Linux:
    # test_serial_connection("/dev/ttyUSB0")