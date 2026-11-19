import os
import random
import unicodedata

import pandas as pd

SEED = 42
N_SYNTH_SCAM = 80   # số mẫu lừa đảo/tin giả sinh theo khuôn
N_SYNTH_LEGIT = 80  # số mẫu hợp lệ cùng chủ đề sinh theo khuôn
OUT_DIR = "data_scam"
# Mẫu thật do bạn tự thu thập. 0.0 = dùng TOÀN BỘ để kiểm tra (khuyến nghị khi còn ít mẫu).
# Khi đã có nhiều (từ khoảng 60 mẫu trở lên), có thể đặt 0.5 để một nửa dùng huấn luyện, một nửa kiểm tra.
REAL_TO_TRAIN_FRACTION = 0.0

random.seed(SEED)

# ---------------------------------------------------------------------------
# Mẫu viết tay. Mẫu chỉ số chẵn dùng để huấn luyện, chỉ số lẻ dành riêng
# cho tập kiểm tra (KHÔNG dùng để huấn luyện).
# ---------------------------------------------------------------------------
SEED_SCAM = [
    "Chúc mừng bạn đã trúng thưởng 50 triệu đồng từ chương trình tri ân khách hàng. Vui lòng chuyển 2 triệu phí nhận thưởng vào tài khoản được cung cấp trong vòng 24 giờ để nhận giải.",
    "Bạn là khách hàng may mắn nhận được một chiếc điện thoại miễn phí. Nhấn vào đường dẫn và điền thông tin thẻ ngân hàng để xác nhận nhận quà.",
    "Thông báo: số điện thoại của bạn trúng giải đặc biệt trị giá 200 triệu. Liên hệ ngay số hotline để làm thủ tục, hết hạn sau hôm nay.",
    "Xin chúc mừng! Bạn vừa trúng xe máy trong chương trình bốc thăm may mắn. Hãy nộp thuế thu nhập 3 triệu đồng trước khi nhận xe.",
    "Mã dự thưởng của bạn đã trúng 1 tỷ đồng. Để rút tiền, vui lòng nạp trước 5 triệu vào ví để xác minh tài khoản.",
    "Bạn được chọn nhận 10 triệu đồng hỗ trợ từ quỹ từ thiện. Gửi số căn cước và mã OTP vừa nhận để chúng tôi chuyển tiền.",
    "Tài khoản ngân hàng của bạn có dấu hiệu bất thường và sẽ bị khóa trong 2 giờ. Nhấn vào đường dẫn để đăng nhập và xác thực ngay.",
    "Ngân hàng thông báo thẻ của bạn hết hạn sử dụng. Vui lòng cung cấp mã OTP gửi về điện thoại để gia hạn thẻ.",
    "Cơ quan công an thông báo bạn liên quan đến một vụ án rửa tiền. Hãy chuyển toàn bộ tiền vào tài khoản an toàn do chúng tôi chỉ định để phục vụ điều tra, tuyệt đối không nói với ai.",
    "Điện lực thông báo hóa đơn tháng này chưa thanh toán, điện sẽ bị cắt trong hôm nay. Liên hệ số này để thanh toán qua tài khoản cá nhân của nhân viên.",
    "Bạn có một bưu kiện bị giữ tại hải quan, cần đóng phí 500 nghìn đồng để được giao. Chuyển khoản gấp để tránh bị hủy đơn.",
    "Bảo hiểm xã hội thông báo bạn được hoàn tiền đóng thừa. Truy cập đường dẫn và nhập thông tin tài khoản để nhận tiền hoàn.",
    "Đơn vị vận chuyển không giao được hàng do sai địa chỉ. Vui lòng bấm vào liên kết để cập nhật địa chỉ và thanh toán phí giao lại.",
    "Đầu tư 5 triệu nhận lãi 30% mỗi tuần, cam kết không rủi ro, rút vốn bất cứ lúc nào. Chỉ còn 10 suất cuối cùng.",
    "Tham gia sàn tiền ảo của chúng tôi, chuyên gia hướng dẫn đảm bảo lợi nhuận mỗi ngày. Nạp càng nhiều nhận thưởng càng lớn.",
    "Hỗ trợ vay 100 triệu không cần thế chấp, giải ngân trong 15 phút. Chỉ cần đóng trước phí hồ sơ 3 triệu đồng.",
    "Nhóm đầu tư kín mời bạn tham gia, vốn nhỏ lãi lớn, người dẫn dắt cam kết đền bù nếu lỗ. Liên hệ để được thêm vào nhóm.",
    "Bạn đã được duyệt khoản vay ưu đãi nhưng cần chuyển tiền bảo hiểm khoản vay trước khi nhận giải ngân.",
    "Kiếm tiền tại nhà chỉ cần thả tim và đánh giá sản phẩm, mỗi ngày 500 nghìn. Nạp tiền làm nhiệm vụ để nhận hoa hồng cao hơn.",
    "Tuyển cộng tác viên làm việc tại nhà, lương 15 đến 30 triệu mỗi tháng, không cần kinh nghiệm. Đóng phí đào tạo 1 triệu để nhận việc.",
    "Cần người nhận hàng hộ, hoa hồng cao mỗi đơn. Chỉ cần cung cấp thông tin cá nhân và thẻ ngân hàng để nhận lương.",
    "Việc nhẹ lương cao cho sinh viên, làm 2 giờ mỗi ngày thu nhập 20 triệu. Đặt cọc 2 triệu để giữ chỗ.",
    "Khẩn cấp: sáng mai cả nước sẽ mất điện 3 ngày vì sự cố lưới điện quốc gia, mọi người mau chia sẻ để người thân biết.",
    "Uống nước chanh pha muối mỗi sáng có thể chữa khỏi hoàn toàn bệnh tiểu đường, bác sĩ không muốn bạn biết bí quyết này.",
    "Cảnh báo có nhóm bắt cóc trẻ em dùng kẹo tẩm thuốc mê ở cổng trường, hãy chia sẻ ngay cho mọi người.",
    "Nhà nước sẽ phát 5 triệu đồng cho mỗi người dân vào tuần sau, bấm vào đường dẫn để đăng ký nhận.",
    "Từ ngày mai ngân hàng sẽ đóng băng toàn bộ tài khoản có số dư trên 50 triệu, hãy rút tiền ngay kẻo mất.",
    "Ăn tỏi sống mỗi ngày giúp diệt sạch mọi loại virus, không cần tiêm vắc xin, thông tin này được giấu kín nhiều năm.",
    "Sốc: ca sĩ nổi tiếng vừa qua đời đột ngột, xem ngay video hé lộ nguyên nhân tại đường dẫn bên dưới.",
    "Uống nước đun sôi để nguội qua đêm sẽ gây ung thư, đừng bao giờ uống, chia sẻ cho người thân ngay.",
]

SEED_LEGIT = [
    "Ngân hàng khuyến cáo khách hàng tuyệt đối không cung cấp mã OTP, mật khẩu hay số thẻ cho bất kỳ ai, kể cả người tự xưng là nhân viên ngân hàng.",
    "Cơ quan công an khuyến cáo người dân cảnh giác với các cuộc gọi giả danh cán bộ yêu cầu chuyển tiền vào tài khoản an toàn, đây là thủ đoạn lừa đảo.",
    "Kết quả xổ số kiến thiết được công bố hằng ngày trên các kênh chính thức của công ty xổ số, người trúng thưởng nhận giải tại điểm đã đăng ký theo quy định.",
    "Công ty thông báo lịch nghỉ Tết Nguyên đán từ ngày 25 tháng Chạp đến hết mùng 5, nhân viên sẽ đi làm lại vào thứ Hai tuần kế tiếp.",
    "Bộ Y tế khuyến cáo người dân rửa tay thường xuyên, đeo khẩu trang nơi đông người và tiêm vắc xin theo lịch của cơ sở y tế.",
    "Hôm nay thời tiết Hà Nội có mưa rào rải rác, nhiệt độ từ 22 đến 28 độ C, người dân nên mang theo áo mưa khi ra đường.",
    "Giá xăng RON 95 được điều chỉnh tăng 300 đồng mỗi lít trong kỳ điều hành chiều nay, theo thông báo của Liên Bộ Tài chính và Công Thương.",
    "Trường thông báo học sinh đi học trở lại từ thứ Hai, phụ huynh vui lòng theo dõi thông báo chính thức trên cổng thông tin của nhà trường.",
    "Tổng đài chăm sóc khách hàng không bao giờ yêu cầu bạn chuyển tiền để nhận quà. Mọi chương trình khuyến mại đều được niêm yết công khai.",
    "Cuộc họp giao ban tháng sẽ diễn ra lúc 9 giờ sáng thứ Sáu tại phòng họp tầng 3, đề nghị các trưởng bộ phận chuẩn bị báo cáo.",
    "Đơn hàng của bạn đã được giao đến địa chỉ đăng ký, vui lòng kiểm tra sản phẩm trước khi thanh toán và giữ lại biên nhận.",
    "Hóa đơn tiền điện tháng này đã được gửi qua ứng dụng chính thức, quý khách thanh toán trước ngày 20 để tránh bị tính phí chậm.",
    "Sở Giáo dục công bố lịch thi tuyển sinh lớp 10 năm nay, thí sinh tra cứu thông tin tại cổng thông tin chính thức của sở.",
    "Doanh nghiệp tuyển dụng nhân viên kế toán, yêu cầu tốt nghiệp đại học chuyên ngành, mức lương theo thỏa thuận, nộp hồ sơ trực tiếp tại văn phòng công ty.",
    "Chương trình khuyến mại mùa lễ giảm giá đến 30 phần trăm cho một số mặt hàng, thời gian áp dụng từ ngày 1 đến ngày 15 tháng này tại cửa hàng.",
    "Ngân hàng Nhà nước điều chỉnh lãi suất điều hành, các ngân hàng thương mại sẽ công bố biểu lãi suất mới trên website chính thức.",
    "Thủ tướng chỉ đạo các bộ ngành tăng cường kiểm tra an toàn thực phẩm dịp cuối năm, xử lý nghiêm các cơ sở vi phạm.",
    "Bệnh viện thông báo lịch khám bệnh ngoài giờ vào thứ Bảy, người bệnh đăng ký khám qua tổng đài hoặc ứng dụng của bệnh viện.",
    "Đội tuyển Việt Nam thắng 2 bàn không gỡ ở trận giao hữu tối qua, huấn luyện viên đánh giá cao tinh thần thi đấu của các cầu thủ.",
    "Bão số 5 đang di chuyển về phía đất liền, các địa phương ven biển được yêu cầu sơ tán dân khỏi khu vực nguy hiểm.",
    "Người dân cần đóng phí gửi xe theo bảng giá niêm yết tại bãi và nhận vé có đóng dấu khi gửi phương tiện.",
    "Cục An toàn thông tin khuyến cáo không bấm vào đường dẫn lạ trong tin nhắn, nên truy cập trực tiếp website chính thức của tổ chức.",
    "Dự án đường cao tốc đoạn qua tỉnh đã hoàn thành 80 phần trăm khối lượng và dự kiến thông xe vào cuối quý sau.",
    "Mời quý khách tham gia hội thảo miễn phí về an toàn thông tin vào sáng Chủ nhật, đăng ký tham dự tại website của ban tổ chức.",
    "Trung tâm kiểm soát bệnh tật ghi nhận số ca sốt xuất huyết tăng, khuyến cáo người dân diệt lăng quăng và ngủ màn.",
    "Thư viện thành phố mở cửa phục vụ bạn đọc từ 8 giờ đến 20 giờ mỗi ngày trong tuần, thẻ thư viện được cấp miễn phí cho học sinh.",
    "Phó chủ tịch UBND tỉnh cho biết kế hoạch hỗ trợ người dân vùng lũ sẽ được triển khai theo danh sách do chính quyền cơ sở lập và công khai.",
    "Sau trận mưa lớn, nhiều tuyến phố bị ngập cục bộ, lực lượng chức năng đã huy động máy bơm để thoát nước cho người dân.",
]


def pick(xs):
    return random.choice(xs)


def fee():
    return pick(["500 nghìn đồng", "1 triệu đồng", "2 triệu đồng", "3 triệu đồng", "5 triệu đồng"])


# ---------------------------------------------------------------------------
# Khuôn sinh mẫu lừa đảo / tin giả (nhãn 1)
# ---------------------------------------------------------------------------
PRIZES = ["một chiếc điện thoại đời mới", "một chiếc xe máy", "10 triệu đồng", "50 triệu đồng",
          "100 triệu đồng", "200 triệu đồng", "1 tỷ đồng", "một chuyến du lịch nước ngoài"]
EVENTS = ["chương trình tri ân khách hàng", "đợt quay số may mắn", "chương trình bốc thăm trúng thưởng",
          "sự kiện kỷ niệm thành lập công ty", "chương trình quay thưởng cuối năm"]
PRIZE_DEMANDS = ["chuyển trước {fee} phí nhận thưởng vào tài khoản được chỉ định",
                 "cung cấp mã OTP vừa gửi về điện thoại để xác nhận",
                 "bấm vào đường dẫn và nhập thông tin thẻ ngân hàng",
                 "nộp thuế thu nhập {fee} trước khi nhận giải",
                 "gửi ảnh căn cước và số tài khoản để chúng tôi chuyển tiền"]
URGENCY = ["trong vòng 24 giờ", "trước cuối ngày hôm nay", "trong 2 giờ tới", "ngay trong hôm nay"]
URGENCY_PRIZE = URGENCY + ["ngay lập tức, nếu chậm giải thưởng sẽ bị hủy", "vì chỉ còn ít suất cuối cùng"]
URGENCY_IMP = URGENCY + ["ngay lập tức, nếu chậm sẽ bị xử lý theo quy định"]


def scam_prize():
    return (f"{pick(['Chúc mừng bạn', 'Xin chúc mừng', 'Thông báo khẩn', 'Bạn là khách hàng may mắn'])}! "
            f"Số điện thoại của bạn đã trúng {pick(PRIZES)} trong {pick(EVENTS)}. "
            f"Vui lòng {pick(PRIZE_DEMANDS).format(fee=fee())} {pick(URGENCY_PRIZE)}.")


IMPERSONATE = [
    ("Ngân hàng", "tài khoản của bạn có dấu hiệu bất thường", "tránh bị khóa tài khoản"),
    ("Ngân hàng", "thẻ của bạn sắp hết hạn sử dụng", "gia hạn thẻ"),
    ("Cơ quan công an", "bạn có liên quan đến một vụ án rửa tiền đang điều tra", "phục vụ công tác điều tra"),
    ("Công ty điện lực", "hóa đơn điện tháng này chưa được thanh toán", "tránh bị cắt điện trong hôm nay"),
    ("Đơn vị vận chuyển", "bưu kiện của bạn đang bị giữ do sai địa chỉ", "nhận lại bưu kiện"),
    ("Bảo hiểm xã hội", "bạn được hoàn lại khoản tiền đóng thừa", "nhận tiền hoàn"),
    ("Hải quan", "bưu kiện gửi cho bạn bị giữ tại cửa khẩu", "được thông quan"),
]
IMP_DEMANDS = ["bấm vào đường dẫn bên dưới và đăng nhập để xác thực",
               "cung cấp mã OTP vừa gửi về điện thoại",
               "chuyển tiền vào tài khoản an toàn do chúng tôi chỉ định và không nói với ai",
               "đóng phí xử lý {fee} qua tài khoản cá nhân của nhân viên"]


def scam_impersonate():
    org, problem, goal = pick(IMPERSONATE)
    return f"{org} thông báo {problem}. Để {goal}, bạn cần {pick(IMP_DEMANDS).format(fee=fee())} {pick(URGENCY_IMP)}."


PITCHES = ["Đầu tư {small} nhận lãi {rate} mỗi tuần", "Làm việc tại nhà chỉ 2 giờ mỗi ngày, thu nhập {income} mỗi tháng",
           "Hỗ trợ vay {loan} không cần thế chấp, giải ngân trong 15 phút",
           "Tham gia nhóm đầu tư kín, vốn nhỏ lãi lớn",
           "Kiếm tiền online chỉ cần thả tim và đánh giá sản phẩm, mỗi ngày {daily}"]
GUARANTEES = ["Cam kết không rủi ro, rút vốn bất cứ lúc nào", "Chuyên gia hướng dẫn đảm bảo có lợi nhuận mỗi ngày",
              "Không cần kinh nghiệm, không cần chứng minh thu nhập", "Đã có hàng nghìn người nhận tiền thành công"]
CALLS = ["Chuyển trước {fee} phí hồ sơ để giữ suất", "Nạp trước {fee} để kích hoạt tài khoản nhận thưởng",
         "Liên hệ ngay để được thêm vào nhóm, chỉ còn vài suất cuối", "Đặt cọc {fee} để nhận việc ngay hôm nay"]


def scam_invest():
    pitch = pick(PITCHES).format(small=pick(["5 triệu", "10 triệu", "20 triệu"]), rate=pick(["20%", "30%", "50%"]),
                                 income=pick(["15 triệu", "20 triệu", "30 triệu"]),
                                 loan=pick(["50 triệu", "100 triệu", "200 triệu"]),
                                 daily=pick(["500 nghìn", "1 triệu"]))
    return f"{pitch}. {pick(GUARANTEES)}. {pick(CALLS).format(fee=fee())}."


ALERTS = ["Khẩn cấp", "Cảnh báo", "Sốc", "Thông tin nóng", "Tin mới nhận được"]
RUMORS = ["sáng mai mạng điện thoại sẽ bị cắt trên toàn quốc", "uống nước gừng nóng mỗi ngày chữa khỏi bệnh huyết áp",
          "ăn hành tây sống diệt được mọi mầm bệnh", "có người lạ phát bánh tẩm thuốc ở cổng chợ",
          "tất cả thẻ ATM sẽ bị khóa vào cuối tuần", "nhà nước hỗ trợ 3 triệu đồng cho mỗi hộ gia đình",
          "một loại thực phẩm quen thuộc bị phát hiện gây ung thư, bộ ngành đang giấu thông tin",
          "ngày mai trường học trên cả nước nghỉ học đột xuất vì lý do đặc biệt"]
SHARES = ["Hãy chia sẻ ngay cho người thân", "Bác sĩ không muốn bạn biết điều này",
          "Mọi người mau chia sẻ trước khi bị xóa", "Bấm vào đường dẫn để biết thêm chi tiết"]


def scam_rumor():
    return f"{pick(ALERTS)}: {pick(RUMORS)}. {pick(SHARES)}."


# ---------------------------------------------------------------------------
# Khuôn sinh mẫu hợp lệ cùng chủ đề (nhãn 0)
# ---------------------------------------------------------------------------
def legit_notice():
    org = pick(["Nhà trường", "Công ty", "Bệnh viện", "Thư viện thành phố", "Ban quản lý chung cư", "Sở Giáo dục"])
    event = pick(["lịch họp giao ban", "lịch nghỉ lễ", "lịch khám bệnh ngoài giờ", "lịch bảo trì thang máy",
                  "kế hoạch phát thẻ thư viện", "lịch tổng vệ sinh khu nhà"])
    when = pick(["vào sáng thứ Sáu", "từ ngày 10 đến ngày 12 tháng này", "vào cuối tuần này", "trong tuần tới"])
    note = pick(["đề nghị mọi người sắp xếp tham dự đúng giờ",
                 "thông tin chi tiết được đăng trên cổng thông tin chính thức",
                 "mọi thắc mắc xin liên hệ bộ phận hành chính trong giờ làm việc"])
    return f"{org} thông báo {event} {when}, {note}."


WARNINGS = [
    ("Ngân hàng", "không cung cấp mã OTP cho bất kỳ ai", "đây là thủ đoạn mà các đối tượng lừa đảo thường sử dụng"),
    ("Cơ quan công an", "cảnh giác với cuộc gọi giả danh yêu cầu chuyển tiền", "các cơ quan chức năng không làm việc qua điện thoại theo cách đó"),
    ("Cục An toàn thông tin", "không bấm vào đường dẫn lạ trong tin nhắn", "nên truy cập trực tiếp website chính thức của tổ chức"),
    ("Bộ Y tế", "rửa tay thường xuyên và tiêm chủng đầy đủ", "theo khuyến cáo mới nhất của cơ quan chức năng"),
    ("Trung tâm kiểm soát bệnh tật", "diệt lăng quăng và ngủ màn để phòng sốt xuất huyết", "số ca mắc đang có xu hướng tăng"),
    ("Ngân hàng Nhà nước", "chỉ giao dịch qua ứng dụng và kênh chính thức của ngân hàng", "để bảo vệ tài sản của chính mình"),
    ("Bộ Công an", "không đăng tải thông tin cá nhân như số căn cước lên mạng xã hội", "kẻ gian có thể lợi dụng để giả mạo danh tính"),
    ("Cục Quản lý Dược", "không tự ý mua thuốc không rõ nguồn gốc qua mạng", "thuốc kém chất lượng có thể gây hại cho sức khỏe"),
    ("Sở Giao thông Vận tải", "giảm tốc độ và bật đèn khi đi qua đoạn đường có sương mù", "để bảo đảm an toàn giao thông"),
]


def legit_warning():
    agency, advice, reason = pick(WARNINGS)
    return f"{agency} khuyến cáo người dân {advice}, {reason}."


def legit_weather():
    t1 = random.randint(20, 27)
    t2 = t1 + random.randint(4, 10)
    return (f"Dự báo {pick(['Hà Nội', 'TP Hồ Chí Minh', 'Đà Nẵng', 'Huế', 'Cần Thơ'])} "
            f"{pick(['có mưa rào rải rác', 'trời nắng nhẹ', 'có mây và gió nhẹ', 'có mưa vừa đến mưa to vào chiều tối'])}, "
            f"nhiệt độ từ {t1} đến {t2} độ C, người dân nên "
            f"{pick(['mang theo áo mưa khi ra đường', 'uống đủ nước khi làm việc ngoài trời', 'theo dõi bản tin dự báo để chủ động công việc'])}.")


def gen_many(fns, n):
    out, seen = [], set()
    tries = i = 0
    while len(out) < n and tries < n * 200:
        tries += 1
        t = fns[i % len(fns)]()
        i += 1
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def norm(t: str) -> str:
    return " ".join(unicodedata.normalize("NFC", str(t)).split())


TXT_HEADERS = {
    "real_scam.txt": (
        "# Mỗi dòng MỘT tin nhắn lừa đảo hoặc tin giả THẬT (nhãn 1).\n"
        "# Dòng trống và dòng bắt đầu bằng dấu # sẽ bị bỏ qua.\n"
        "# Trước khi dán: xóa số điện thoại, tên người, số tài khoản và đường dẫn.\n"
    ),
    "real_legit.txt": (
        "# Mỗi dòng MỘT tin nhắn hoặc đoạn tin hợp lệ THẬT (nhãn 0).\n"
        "# Nên chọn loại dễ nhầm với lừa đảo: thông báo ngân hàng, giao hàng, khuyến mại, cảnh báo lừa đảo chính thống.\n"
        "# Dòng trống và dòng bắt đầu bằng dấu # sẽ bị bỏ qua.\n"
    ),
}


def read_lines(path):
    out = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            t = line.strip()
            if t and not t.startswith("#"):
                out.append(t)
    return out


def load_real():
    """Đọc mẫu thật từ real_scam.txt, real_legit.txt và (nếu có) real_collected.csv."""
    for name, header in TXT_HEADERS.items():
        path = os.path.join(OUT_DIR, name)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(header)

    rows = []
    for name, label in (("real_scam.txt", 1), ("real_legit.txt", 0)):
        rows += [(norm(t), label) for t in read_lines(os.path.join(OUT_DIR, name))]

    csv_path = os.path.join(OUT_DIR, "real_collected.csv")
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            for _, r in df.iterrows():
                if isinstance(r["text"], str) and r["text"].strip() and int(r["label"]) in (0, 1):
                    rows.append((norm(r["text"]), int(r["label"])))
        except pd.errors.EmptyDataError:
            pass

    seen, unique = set(), []
    for t, label in rows:
        if t not in seen:
            seen.add(t)
            unique.append((t, label))
    return unique


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    synth_scam = gen_many([scam_prize, scam_impersonate, scam_invest, scam_rumor], N_SYNTH_SCAM)
    synth_legit = gen_many([legit_notice, legit_warning, legit_weather], N_SYNTH_LEGIT)

    train_rows = [(norm(t), 1) for t in synth_scam + SEED_SCAM[0::2]]
    train_rows += [(norm(t), 0) for t in synth_legit + SEED_LEGIT[0::2]]
    eval_rows = [(norm(t), 1) for t in SEED_SCAM[1::2]] + [(norm(t), 0) for t in SEED_LEGIT[1::2]]

    # Mẫu thật do người dùng tự thu thập
    known = {t for t, _ in train_rows} | {t for t, _ in eval_rows}
    real = [(t, y) for t, y in load_real() if t not in known]
    random.Random(SEED).shuffle(real)
    k = int(len(real) * REAL_TO_TRAIN_FRACTION)
    train_rows += real[:k]
    eval_rows += real[k:]
    n_real = len(real)

    random.shuffle(train_rows)
    pd.DataFrame(train_rows, columns=["text", "label"]).to_csv(
        os.path.join(OUT_DIR, "train_synth.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(eval_rows, columns=["text", "label"]).to_csv(
        os.path.join(OUT_DIR, "scam_eval.csv"), index=False, encoding="utf-8-sig")

    n1 = sum(1 for _, y in train_rows if y == 1)
    print(f"train_synth.csv: {len(train_rows)} mẫu (lừa đảo/tin giả {n1}, hợp lệ {len(train_rows) - n1})")
    e1 = sum(1 for _, y in eval_rows if y == 1)
    print(f"scam_eval.csv  : {len(eval_rows)} mẫu (lừa đảo/tin giả {e1}, hợp lệ {len(eval_rows) - e1})")
    r1 = sum(1 for _, y in real if y == 1)
    print(f"Mẫu thật bạn thêm: {n_real} (lừa đảo {r1}, hợp lệ {n_real - r1}) | dùng huấn luyện: {k} | dùng kiểm tra: {n_real - k}")
    if n_real == 0:
        print("  (chưa có mẫu thật, hãy dán vào data_scam/real_scam.txt và data_scam/real_legit.txt)")
    print("\nVí dụ mẫu sinh theo khuôn:")
    for t in (synth_scam[0], synth_scam[25], synth_legit[0], synth_legit[40]):
        print(" -", t)


if __name__ == "__main__":
    main()
