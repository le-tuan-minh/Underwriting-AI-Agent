from app_groq.schemas import (
    AgentAOutput, ValidationResults, MatchedDocument,
    CrossCheckResults, ConflictItem, FieldValue,
)

MOCK_INPUT = AgentAOutput(
    success=True,
    loan_profile_type="Vay thế chấp bất động sản",
    validation_results=ValidationResults(
        analysis=(
            "Bộ hồ sơ sản phẩm 'Vay thế chấp bất động sản' KHÔNG ĐỦ ĐIỀU KIỆN thẩm định "
            "do THIẾU các chứng từ bắt buộc: Báo cáo đề xuất cấp tín dụng kiêm tờ trình "
            "thẩm định (Do Cán bộ tín dụng lập)."
        ),
        matched_documents=[
            MatchedDocument(
                checklist_id="cccd",
                checklist_item="Ảnh chụp màn hình hoặc file chứa thông tin định danh - "
                               "căn cước công dân của Khách hàng (và vợ/chồng nếu có)",
                file_assigned="cccd.jpg",
                actual_option_used=None,
                sub_document_id=None,
                group="1_Pháp lý nhân thân",
                status="Valid",
            ),
            MatchedDocument(
                checklist_id="de_nghi_vay_von",
                checklist_item="Giấy đề nghị vay vốn kiêm Phương án hiện thực hóa (Mẫu Ngân hàng)",
                file_assigned="Don_vay.pdf",
                actual_option_used=None,
                sub_document_id=None,
                group="2_Phương án vay",
                status="Valid",
            ),
            MatchedDocument(
                checklist_id="hd_dat_coc_nha",
                checklist_item="Hợp đồng đặt cọc/Hợp đồng chuyển nhượng quyền sử dụng đất "
                               "và tài sản gắn liền với đất",
                file_assigned="HD_coc.pdf",
                actual_option_used=None,
                sub_document_id=None,
                group="2_Phương án vay",
                status="Valid",
            ),
            MatchedDocument(
                checklist_id="chung_minh_thu_nhap_tu_luong",
                checklist_item="Chứng từ nguồn thu nhập từ lương",
                file_assigned="Sao_ke.pdf",
                actual_option_used="luong_chuyen_khoan",
                sub_document_id="sao_ke_thu_nhap",
                group="3_Nguồn thu nhập",
                status="Valid",
            ),
            MatchedDocument(
                checklist_id="so_do_gcn_qsdđ",
                checklist_item="Giấy chứng nhận QSDĐ, QSHN và TSTGLVĐ (Sổ đỏ/Sổ hồng) "
                               "của tài sản mua/thế chấp",
                file_assigned="So_huu_dat.pdf",
                actual_option_used=None,
                sub_document_id=None,
                group="5_Tài sản bảo đảm",
                status="Valid",
            ),
            MatchedDocument(
                checklist_id="chung_thu_dinh_gia",
                checklist_item="Chứng thu/Biên bản định giá tài sản bảo đảm "
                               "(Do ngân hàng hoặc công ty định giá độc lập cấp)",
                file_assigned="TSBD.pdf",
                actual_option_used=None,
                sub_document_id=None,
                group="5_Tài sản bảo đảm",
                status="Valid",
            ),
        ],
        # Giờ là tên tiếng Việt đầy đủ, KHÔNG phải ID
        missing_mandatory_documents=[
            "Báo cáo đề xuất cấp tín dụng kiêm tờ trình thẩm định (Do Cán bộ tín dụng lập)",
        ],
        missing_optional_documents=[
            "Thông tin cư trú tra cứu qua VNeID",
            "Giấy chứng nhận kết hôn hoặc Giấy xác nhận tình trạng độc thân",
            "Giấy chứng nhận đăng ký doanh nghiệp (ĐKDN)",
            "Báo cáo tài chính tối thiểu 01 năm gần nhất (hoặc Tờ khai quyết toán thuế)",
            "Sao kê tài khoản thanh toán của Doanh nghiệp (tối thiểu 6 tháng gần nhất)",
            "Giấy chứng nhận sở hữu tài sản cho thuê (Sổ đỏ nhà/Đăng ký xe...)",
            "Hợp đồng cho thuê tài sản còn hiệu lực pháp lý",
            "Chứng từ chứng minh nhận tiền thuê (Sao kê tài khoản hoặc Biên nhận tiền)",
            "Hợp đồng tín dụng và Lịch trả nợ của các khoản vay đang còn dư nợ tại TCTD khác",
        ],
        is_eligible_for_review=False,
    ),
    cross_check_results=CrossCheckResults(
        is_consistent=False,
        conflicts_found=[
            ConflictItem(
                field_name="Ngày sinh",
                values=[
                    FieldValue(file_name="cccd.jpg",    document_id="cccd",           value="15/02/1990"),
                    FieldValue(file_name="Don_vay.pdf", document_id="de_nghi_vay_von", value="15/10/1988"),
                ],
                majority_value=None,
                conflicting_files=["cccd.jpg", "Don_vay.pdf"],
                reason="Giá trị ngày sinh không khớp nhau",
            ),
            ConflictItem(
                field_name="Số CCCD",
                values=[
                    FieldValue(file_name="Bang_luong.pdf", document_id="xac_nhan_bang_luong", value="001088012345"),
                    FieldValue(file_name="cccd.jpg",       document_id="cccd",                value="578302649171"),
                    FieldValue(file_name="Don_vay.pdf",    document_id="de_nghi_vay_von",     value="001088012345"),
                    FieldValue(file_name="HD_coc.pdf",     document_id="hd_dat_coc_nha",      value="001088012345"),
                ],
                majority_value="001088012345",
                conflicting_files=["cccd.jpg"],
                reason="Giá trị số CCCD không khớp nhau",
            ),
        ],
    ),
    error=None,
)