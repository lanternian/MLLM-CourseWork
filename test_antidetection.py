#!/usr/bin/env python3
"""
测试反检测功能的脚本
用于验证Playwright Stealth是否生效
"""

from web_agent.config import Settings
from web_agent.browser import BrowserController, STEALTH_AVAILABLE


def test_antidetection():
    """测试反检测功能"""
    print("=" * 60)
    print("反检测功能测试")
    print("=" * 60)
    
    # 检查stealth库是否可用
    if STEALTH_AVAILABLE:
        print("✅ playwright-stealth 已安装")
    else:
        print("⚠️ playwright-stealth 未安装")
        print("   将使用基础反检测措施")
        print("   安装命令: pip install playwright-stealth")
    
    # 创建配置（非headless模式便于观察）
    settings = Settings.from_env()
    settings.headless = False  # 改为False便于观察
    
    print(f"\n配置信息:")
    print(f"  - headless: {settings.headless}")
    print(f"  - model: {settings.model}")
    print(f"  - max_steps: {settings.max_steps}")
    
    # 创建浏览器控制器
    artifact_dir = settings.artifacts_dir / "test_antidetection"
    
    print(f"\n正在启动浏览器...")
    browser = BrowserController(settings, artifact_dir)
    
    try:
        browser.start()
        print("✅ 浏览器启动成功")
        
        # 测试1: 访问检测页面
        print("\n" + "=" * 60)
        print("测试1: 访问反检测检测页面")
        print("=" * 60)
        print("正在访问: https://bot.sannysoft.com/")
        browser.open("https://bot.sannysoft.com/")
        browser.page.wait_for_timeout(3000)
        print("✅ 页面加载完成")
        print("   请查看浏览器窗口，检查是否有自动化检测警告")
        
        # 测试2: 访问百度
        print("\n" + "=" * 60)
        print("测试2: 访问百度搜索")
        print("=" * 60)
        print("正在访问: https://www.baidu.com/")
        browser.open("https://www.baidu.com/")
        browser.page.wait_for_timeout(2000)
        
        # 检测验证码
        print("\n检测验证码...")
        captcha_result = browser.detect_captcha()
        if captcha_result["detected"]:
            print(f"⚠️ {captcha_result['message']}")
            print("   如需测试人工介入，请在浏览器中手动完成验证")
        else:
            print("✅ 未检测到验证码")
        
        # 测试搜索功能
        print("\n测试搜索功能...")
        try:
            search_box = browser.page.locator("#kw")
            if search_box.count() > 0:
                search_box.fill("多模态 Agent")
                browser.page.wait_for_timeout(500)
                search_box.press("Enter")
                browser.page.wait_for_timeout(3000)
                print(f"✅ 搜索完成，当前URL: {browser.page.url}")
            else:
                print("⚠️ 未找到搜索框")
        except Exception as e:
            print(f"❌ 搜索失败: {e}")
        
        # 测试3: 访问B站
        print("\n" + "=" * 60)
        print("测试3: 访问哔哩哔哩")
        print("=" * 60)
        print("正在访问: https://www.bilibili.com/")
        browser.open("https://www.bilibili.com/")
        browser.page.wait_for_timeout(2000)
        
        # 检测验证码
        captcha_result = browser.detect_captcha()
        if captcha_result["detected"]:
            print(f"⚠️ {captcha_result['message']}")
        else:
            print("✅ 未检测到验证码")
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        print("\n浏览器将保持打开状态 10 秒，便于观察...")
        browser.page.wait_for_timeout(10000)
        
    except Exception as e:
        print(f"\n❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n正在关闭浏览器...")
        browser.close()
        print("✅ 测试结束\n")


def test_captcha_detection():
    """单独测试验证码检测功能"""
    print("\n" + "=" * 60)
    print("验证码检测功能测试")
    print("=" * 60)
    
    settings = Settings.from_env()
    settings.headless = False
    
    browser = BrowserController(settings, settings.artifacts_dir / "test_captcha")
    
    try:
        browser.start()
        
        # 测试各种检测页面
        test_urls = [
            ("正常页面", "https://www.baidu.com/"),
            ("reCAPTCHA demo", "https://www.google.com/recaptcha/api2/demo"),
        ]
        
        for name, url in test_urls:
            print(f"\n测试: {name}")
            print(f"URL: {url}")
            try:
                browser.open(url)
                browser.page.wait_for_timeout(2000)
                
                result = browser.detect_captcha()
                if result["detected"]:
                    print(f"  检测结果: ✅ 已检测到 ({result['type']})")
                else:
                    print(f"  检测结果: ⚠️ 未检测到")
            except Exception as e:
                print(f"  错误: {e}")
        
        print("\n测试完成，5秒后关闭...")
        browser.page.wait_for_timeout(5000)
        
    finally:
        browser.close()


if __name__ == "__main__":
    import sys
    
    print("选择测试模式:")
    print("  1. 完整反检测测试")
    print("  2. 仅测试验证码检测")
    print("  3. 两者都测试")
    
    choice = input("\n请选择 (1/2/3, 默认1): ").strip() or "1"
    
    if choice == "1":
        test_antidetection()
    elif choice == "2":
        test_captcha_detection()
    elif choice == "3":
        test_antidetection()
        test_captcha_detection()
    else:
        print("无效选择，运行默认测试...")
        test_antidetection()
