# Suspicious actions
SUSPICIOUS_ACTIONS = {
    'looking_away': 'Nhìn ra ngoài màn hình',
    'multiple_faces': 'Nhiều người trong khung hình',
    'phone_usage': 'Sử dụng điện thoại',
    'talking': 'Đang nói chuyện',
    'leaving_frame': 'Rời khỏi khung hình',
    'cheating_device': 'Phát hiện thiết bị gian lận',
    'face_occluded': 'Che mặt',
    'eye_closed': 'Nhắm mắt quá lâu',
}

# Violation severity (1-5, 5 is most severe)
VIOLATION_SEVERITY = {
    'looking_away': 2,
    'multiple_faces': 4,
    'phone_usage': 5,
    'talking': 3,
    'leaving_frame': 4,
    'cheating_device': 5,
    'face_occluded': 3,
    'eye_closed': 1,
}