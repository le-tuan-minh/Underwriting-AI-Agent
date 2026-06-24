from app_groq.schemas import AgentAOutput, MatchedDocument

# Mock input khớp chính xác với output format Agent A đã cập nhật
MOCK_INPUT = AgentAOutput(
    analysis=(
        "Bộ hồ sơ của khách hàng có một số chứng từ phù hợp với yêu cầu "
        "của checklist, nhưng vẫn còn thiếu một số giấy tờ quan trọng"
    ),
    matched_documents=[
        MatchedDocument(
            checklist_item="1.1_Chung_tu_nhan_than",
            file_assigned="01_cccd_front.png",
            status="Valid",
        ),
        MatchedDocument(
            checklist_item="1.1_Chung_tu_nhan_than",
            file_assigned="02_vneid_screenshot.png",
            status="Valid",
        ),
        MatchedDocument(
            checklist_item="1.2_Chung_tu_nguon_thu",
            file_assigned="04_giay_phep_dkkd.pdf",
            status="Valid",
        ),
        MatchedDocument(
            checklist_item="1.2_Chung_tu_nguon_thu",
            file_assigned="05_hoa_don_vat.png",
            status="Valid",
        ),
        MatchedDocument(
            checklist_item="1.2_Chung_tu_nguon_thu",
            file_assigned="06_sao_ke_tai_khoan.pdf",
            status="Valid",
        ),
        MatchedDocument(
            checklist_item="1.4_Chung_tu_Phuong_an_vay",
            file_assigned="03_don_de_nghi_vay_von.pdf",
            status="Valid",
        ),
    ],
    missing_documents=[
        "Giay_dang_ky_ket_hon",
        "Bao_cao_tai_chinh_BCTC",
        "Giay_to_ton_tai_GCN_HDMB",
        "Hop_dong_cho_thue",
        "Chung_tu_nhan_tien_thue",
        "Anh_cho_thue",
        "Hop_dong_tin_dung_HDTD",
        "Hop_dong_dat_coc_nha",
        "GCN_QSDĐ",
        "Giay_to_phap_ly_TSBD_GCN_QSDĐ",
        "Chung_thu_dinh_gia",
        "Bao_cao_de_xuat_cap_tin_dung",
    ],
    is_eligible_for_review=False,
)