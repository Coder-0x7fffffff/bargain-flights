#!/usr/bin/env python3
"""
二维码生成工具 - 纯 Python 实现，无外部依赖
使用免费 API 生成二维码图片

用法:
  python3 qrcode.py --url "https://xxx" --output "qrcode.png"
  python3 qrcode.py -u "https://xxx" -o "qrcode.png"

也可以直接获取二维码 URL（用于展示）:
  python3 qrcode.py --url "https://xxx" --url-only
"""

import argparse
import urllib.request
import urllib.parse
import os
import sys


def get_qrcode_url(url: str, size: int = 300) -> str:
    """
    生成二维码图片的 URL（使用免费 API）
    
    Args:
        url: 需要编码的链接
        size: 图片尺寸（像素）
    
    Returns:
        二维码图片的 URL
    """
    encoded_url = urllib.parse.quote(url, safe='')
    return f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={encoded_url}"


def download_qrcode(url: str, output_path: str, size: int = 300) -> bool:
    """
    下载二维码图片到本地
    
    Args:
        url: 需要编码的链接
        output_path: 输出图片路径
        size: 图片尺寸（像素）
    
    Returns:
        是否成功
    """
    qrcode_url = get_qrcode_url(url, size)
    
    try:
        # 创建输出目录（如果不存在）
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 下载图片
        with urllib.request.urlopen(qrcode_url, timeout=10) as response:
            image_data = response.read()
        
        # 保存到本地
        with open(output_path, 'wb') as f:
            f.write(image_data)
        
        return True
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return False


def generate_qrcode_terminal(url: str, size: int = 300) -> str:
    """
    生成终端可显示的二维码（返回 URL，用户可在浏览器查看）
    
    Args:
        url: 需要编码的链接
        size: 图片尺寸
    
    Returns:
        二维码图片 URL
    """
    return get_qrcode_url(url, size)


def main():
    parser = argparse.ArgumentParser(
        description='生成二维码图片，方便手机扫码访问预订链接'
    )
    parser.add_argument(
        '--url', '-u',
        required=True,
        help='需要编码的链接'
    )
    parser.add_argument(
        '--output', '-o',
        default=None,
        help='输出图片路径（默认当前目录 qrcode.png）'
    )
    parser.add_argument(
        '--url-only',
        action='store_true',
        help='只输出二维码图片 URL，不下载'
    )
    parser.add_argument(
        '--size', '-s',
        type=int,
        default=300,
        help='图片尺寸（像素），默认 300'
    )
    
    args = parser.parse_args()
    
    # 只输出 URL
    if args.url_only:
        qrcode_url = get_qrcode_url(args.url, args.size)
        print(qrcode_url)
        return
    
    # 确定输出路径
    output_path = args.output or os.path.join(os.getcwd(), 'qrcode.png')
    
    # 下载二维码
    if download_qrcode(args.url, output_path, args.size):
        print(f"✅ 二维码已生成: {output_path}")
        print(f"🔗 链接: {args.url}")
        print(f"🌐 在线查看: {get_qrcode_url(args.url, args.size)}")


if __name__ == '__main__':
    main()