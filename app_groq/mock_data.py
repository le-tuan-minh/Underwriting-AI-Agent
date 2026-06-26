from app_groq.schemas import AgentAOutput, ValidationResults, MatchedDocument

MOCK_INPUT = AgentAOutput(
    success=True,
    loan_profile_type="Vay thế chấp bất động sản",
    validation_results=ValidationResults(
        analysis=(
            "Danh sách hồ sơ của khách hàng đã được đối chiếu với Bộ Checklist sản phẩm chuẩn. "
            "Kết quả cho thấy khách hàng đã cung cấp hầu hết các chứng từ cần thiết, "
            "tuy nhiên vẫn còn một số chứng từ thiếu hoặc không hợp lệ."
        ),
        matched_documents=[
            MatchedDocument(
                checklist_id="cccd",
                checklist_item="CCCD/Hộ chiếu của Khách hàng vay và người đồng trách nhiệm (nếu có)",
                file_assigned="01_cccd_front.png",
                actual_option_used=None,
                sub_document_id=None,
                group="1_Pháp lý nhân thân",
                status="Valid",
            ),
            MatchedDocument(
                checklist_id="cu_tru_vneid",
                checklist_item="Thông tin cư trú tra cứu qua VNeID",
                file_assigned="02_vneid_screenshot.png",
                actual_option_used=None,
                sub_document_id=None,
                group="1_Pháp lý nhân thân",
                status="Valid",
            ),
            MatchedDocument(
                checklist_id="de_nghi_vay_von",
                checklist_item="Giấy đề nghị vay vốn kiêm Phương án hiện thực hóa (Mẫu Ngân hàng)",
                file_assigned="03_don_de_nghi_vay_von.pdf",
                actual_option_used=None,
                sub_document_id=None,
                group="2_Phương án vay",
                status="Valid",
            ),
            MatchedDocument(
                checklist_id="dk_doanh_nghiep",
                checklist_item="Giấy chứng nhận đăng ký doanh nghiệp (ĐKDN)",
                file_assigned="04_giay_phep_dkkd.pdf",
                actual_option_used="thu_nhap_doanh_nghiep",
                sub_document_id="dk_doanh_nghiep",
                group="3_Nguồn thu nhập",
                status="Valid",
            ),
            MatchedDocument(
                checklist_id="sao_ke_tk_cty",
                checklist_item="Sao kê tài khoản thanh toán của Doanh nghiệp (tối thiểu 6 tháng gần nhất)",
                file_assigned="06_sao_ke_tai_khoan.pdf",
                actual_option_used="thu_nhap_doanh_nghiep",
                sub_document_id="sao_ke_tk_cty",
                group="3_Nguồn thu nhập",
                status="Valid",
            ),
        ],
        missing_mandatory_documents=[
            "hd_dat_coc_nha",
            "so_do_gcn_qsdđ",
            "chung_thu_dinh_gia",
            "bao_cao_de_xuat",
        ],
        missing_optional_documents=[
            "tinh_trang_hon_nhan",
            "hd_tin_dung_tctd",
        ],
        is_eligible_for_review=False,
    ),
    error=None,
)