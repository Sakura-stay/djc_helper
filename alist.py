import os
from urllib.parse import quote

import requests

from dao import ConfigInterface, to_raw_type
from log import color, logger
from util import get_now, human_readable_size, with_cache

SERVER_ADDR = "http://114.132.252.185:5244"

API_LOGIN = f"{SERVER_ADDR}/api/auth/login"
API_UPLOAD = f"{SERVER_ADDR}/api/fs/put"


class CommonResponse(ConfigInterface):
    def __init__(self):
        self.code = 200
        self.message = "success"
        self.data = {}


def generate_exception(res: CommonResponse, ctx: str) -> Exception:
    return Exception(f"alist {ctx} failed, code={res.code}, message={res.message}")


class LoginRequest(ConfigInterface):
    def __init__(self):
        self.username = ""
        self.password = ""
        self.otp_code = ""


class LoginResponse(ConfigInterface):
    def __init__(self):
        self.token = ""


def login(username: str, password: str, otp_code: str = "") -> str:
    """
    登录alist，获取上传所需token
    """
    return with_cache(
        "alist",
        "login",
        cache_max_seconds=24 * 60 * 60,
        cache_miss_func=lambda: _login(username, password, otp_code)
    )


def _login(username: str, password: str, otp_code: str = "") -> str:
    req = LoginRequest()
    req.username = username
    req.password = password
    req.otp_code = otp_code

    raw_res = requests.post(API_LOGIN, json=to_raw_type(req))

    res = CommonResponse().auto_update_config(raw_res.json())
    if res.code != 200:
        raise generate_exception(res, "login")

    data = LoginResponse().auto_update_config(res.data)

    return data.token


def format_remote_file_path(remote_file_path: str) -> str:
    """
    确保远程路径以 / 开头
    """
    if not remote_file_path.startswith("/"):
        remote_file_path = "/" + remote_file_path

    return remote_file_path


def upload(local_file_path: str, remote_file_path: str):
    username = os.getenv("ALIST_USERNAME")
    password = os.getenv("ALIST_PASSWORD")

    remote_file_path = format_remote_file_path(remote_file_path)

    actual_size = os.stat(local_file_path).st_size
    file_size = human_readable_size(actual_size)

    logger.info(f"开始上传 {local_file_path} ({file_size}) 到网盘，远程路径为 {remote_file_path}")

    start_time = get_now()

    with open(local_file_path, "rb") as file_to_upload:
        raw_res = requests.put(API_UPLOAD, data=file_to_upload, headers={
            "File-Path": quote(remote_file_path),
            "As-Task": "false",
            "Authorization": login(username, password),
        })

        res = CommonResponse().auto_update_config(raw_res.json())
        if res.code != 200:
            raise generate_exception(res, "upload")

    end_time = get_now()
    used_time = end_time - start_time

    speed = actual_size / used_time.total_seconds()
    human_readable_speed = human_readable_size(speed)

    logger.info(color("bold_yellow") + f"上传完成，耗时 {used_time}({human_readable_speed}/s)")


def get_download_url(remote_file_path: str):
    remote_file_path = format_remote_file_path(remote_file_path)

    return f"{SERVER_ADDR}/d{remote_file_path}"


def demo_login():
    username = os.getenv("ALIST_USERNAME")
    password = os.getenv("ALIST_PASSWORD")

    cached_token = login(username, password)
    print(f"cached_token   = {cached_token}")

    uncached_token = _login(username, password)
    print(f"uncached_token = {uncached_token}")


def demo_upload():
    upload(
        "C:/Users/fzls/Downloads/chromedriver_102.exe",
        "/文本编辑器、chrome浏览器、autojs、HttpCanary等小工具/chromedriver_102.exe",
    )


def demo_download():
    url = get_download_url("/文本编辑器、chrome浏览器、autojs、HttpCanary等小工具/chromedriver_102.exe")

    from download import download_file
    download_file(url)


if __name__ == '__main__':
    # demo_login()
    # demo_upload()
    demo_download()