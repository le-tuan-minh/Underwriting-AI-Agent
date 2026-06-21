from app.schemas import AgentAOutput

MOCK_INPUT = AgentAOutput(
    document_id="HS001",
    document_type="Hợp đồng lao động",
    summary="""
        Hợp đồng lao động giữa công ty ABC và ông Nguyễn Văn A.
        Thời hạn: 12 tháng, bắt đầu từ 01/01/2024.
        Mức lương: 15,000,000 VNĐ/tháng.
        Chức vụ: Nhân viên kinh doanh.
    """,
    checklist={
        "có chữ ký hai bên": True,
        "có đóng dấu công ty": False,
        "thời hạn hợp đồng rõ ràng": True,
        "mức lương được ghi rõ": True,
        "có xác nhận ngày tháng": False,
    }
)