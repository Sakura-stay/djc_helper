import json
import os.path

from const import downloads_dir
from data_struct import to_raw_type
from first_run import *
from update import version_less
from upload_lanzouyun import Uploader


class NoticeShowType:
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ALWAYS = "always"
    DEPRECATED = "deprecated"


valid_notice_show_type = set(val for attr, val in NoticeShowType.__dict__.items() if not attr.startswith("__"))


class Notice(ConfigInterface):
    def __init__(self):
        self.sender = "风之凌殇"
        self.title = "测试消息标题"
        self.message = "测试消息内容"
        self.send_at = "2021-05-11 00:00:00"
        self.show_type = NoticeShowType.ONCE
        self.open_url = ""  # 若填入，在展示对应公告时会弹出该网页
        self.expire_at = "2121-05-11 00:00:00"
        self.show_only_before_version = now_version  # 若填入，则仅在对应版本前才会展示

    def __lt__(self, other):
        return parse_time(self.send_at) < parse_time(other.send_at)

    def need_show(self) -> bool:
        key = self.get_first_run_key()

        # 判断是否过期
        if get_now() > parse_time(self.expire_at):
            return False

        # 判断是否满足版本需求
        if self.show_only_before_version != "" and not version_less(now_version, self.show_only_before_version):
            return False

        # 根据显示类型判断
        if self.show_type == NoticeShowType.ONCE:
            return is_first_run(key)
        elif self.show_type == NoticeShowType.DAILY:
            return is_daily_first_run(key)
        elif self.show_type == NoticeShowType.WEEKLY:
            return is_weekly_first_run(key)
        elif self.show_type == NoticeShowType.MONTHLY:
            return is_monthly_first_run(key)
        elif self.show_type == NoticeShowType.ALWAYS:
            return True
        elif self.show_type == NoticeShowType.DEPRECATED:
            return False
        else:
            return False

    def reset_first_run(self):
        reset_first_run(self.get_first_run_key())

    def get_first_run_key(self) -> str:
        return f"notice_need_show_{self.title}_{self.send_at}"


class NoticeManager:
    def __init__(self, load_from_remote=True):
        self.notices = []  # type: List[Notice]

        self.file_name = "notices.txt"
        self.cache_path = f"{downloads_dir}/{self.file_name}"
        self.save_path = f"utils/{self.file_name}"

        self.load(load_from_remote)

    @try_except()
    def load(self, from_remote=True):
        if from_remote:
            path = self.cache_path
            # 下载最新公告
            self.download_latest_notices()
        else:
            path = self.save_path

        if not os.path.isfile(path):
            return

        # 读取公告
        with open(path, 'r', encoding='utf-8') as save_file:
            for raw_notice in json.load(save_file):
                notice = Notice().auto_update_config(raw_notice)
                self.notices.append(notice)

        self.notices = sorted(self.notices)
        logger.info("公告读取完毕")

    def download_latest_notices(self):
        uploader = Uploader()

        dirpath, filename = os.path.dirname(self.cache_path), os.path.basename(self.cache_path)
        uploader.download_file_in_folder(uploader.folder_online_files, filename, dirpath, try_compressed_version_first=True)

    @try_except()
    def save(self):
        # 本地存盘
        with open(self.save_path, 'w', encoding='utf-8') as save_file:
            json.dump(to_raw_type(self.notices), save_file, ensure_ascii=False, indent=2)
            logger.info("公告存盘完毕")

        # 上传到网盘
        uploader = Uploader()
        with open("upload_cookie.json") as fp:
            cookie = json.load(fp)
        uploader.login(cookie)
        uploader.upload_to_lanzouyun(self.save_path, uploader.folder_online_files, delete_history_file=True, also_upload_compressed_version=True)

    @try_except()
    def show_notices(self):
        valid_notices = list(filter(lambda notice: notice.need_show(), self.notices))

        logger.info(f"发现 {len(valid_notices)} 个新公告")
        for idx, notice in enumerate(valid_notices):
            # 展示公告
            message_box(notice.message, f"公告({idx + 1}/{len(valid_notices)}) - {notice.title}", icon=win32con.MB_ICONINFORMATION, open_url=notice.open_url, follow_flag_file=False)

        logger.info("所有需要展示的公告均已展示完毕")

    def add_notice(self, title, message, sender="风之凌殇", send_at=format_now(), show_type=NoticeShowType.ONCE, open_url="", valid_duration=timedelta(days=7), show_only_before_version=""):
        if show_type not in valid_notice_show_type:
            logger.error(f"无效的show_type={show_type}，有效值为{valid_notice_show_type}")
            return

        for old_notice in self.notices:
            if old_notice.title == title and old_notice.message == message and old_notice.sender == sender:
                logger.error(f"发现内容完全一致的公告，请确定是否是误操作，若非误操作请去文本直接修改。\n{old_notice}")
                return

        notice = Notice()
        notice.title = title
        notice.message = message
        notice.sender = sender
        notice.send_at = send_at
        notice.show_type = show_type
        notice.open_url = open_url
        notice.expire_at = format_time(get_now() + valid_duration)
        notice.show_only_before_version = show_only_before_version

        self.notices.append(notice)
        logger.info(f"添加公告：{notice}")


def main():
    # 初始化
    nm = NoticeManager(load_from_remote=False)

    # note: 在这里添加公告
    title = "分享一个较低成本且方便地在手机上间接运行小助手和dnf挂时长和小游戏的方案"
    message = """昨天在腾讯云花134元买了个2c4g8m的云服务器，本来是准备用作其他用途的，只是暂时用不到。在选择镜像时发现可以装windows2019服务器，就想着可不可以用来运行小助手，甚至说运行DNF？
于是折腾了一波，发现还真行，运行小助手很流畅，DNF的话可以正常进入并操作，只是因为配置问题，只能挂挂时长或者小游戏了，刷图是太卡了。
而且微软的远程桌面在安卓、iOS的手机和pad上都有官方的app，可以很轻松的配置并一键连接，就可以实现在外面的时候也能在手机中间接地轻易运行小助手了

录了个视频，介绍了下整体流程，大家有兴趣的可以看看哈~

"""
    open_url = "https://www.bilibili.com/video/BV18f4y1M7uL/"
    nm.add_notice(title, message,
                  send_at=format_now(),
                  show_type=NoticeShowType.ONCE, open_url=open_url, valid_duration=timedelta(days=7),
                  show_only_before_version=now_version,
                  # show_only_before_version="",
                  )

    nm.save()


def test():
    nm = NoticeManager(load_from_remote=False)

    for notice in nm.notices:
        notice.reset_first_run()
        notice.show_only_before_version = ""

    logger.info("测试环境已重置完毕，所有公告都已改为未展示状态，且关闭版本限制")

    nm.show_notices()

    os.system("PAUSE")


if __name__ == '__main__':
    TEST = False
    bypass_proxy()

    if not TEST:
        main()
    else:
        test()
