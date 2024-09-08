from flask import Flask, request, send_file
import undetected_chromedriver as uc
import re
import os
from threading import Timer
import time

driver = None
XVFB_DISPLAY = None
USER_AGENT = None
CHROME_EXE_PATH = None
timer = None

app = Flask(__name__)

def _start_xvfb_display():
    global XVFB_DISPLAY
    if XVFB_DISPLAY is None:
        from xvfbwrapper import Xvfb
        XVFB_DISPLAY = Xvfb()
        XVFB_DISPLAY.start()

def get_chrome_exe_path() -> str:
    global CHROME_EXE_PATH
    if CHROME_EXE_PATH is not None:
        return CHROME_EXE_PATH
    chrome_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chrome', "chrome")
    if os.path.exists(chrome_path):
        CHROME_EXE_PATH = chrome_path
        return CHROME_EXE_PATH
    CHROME_EXE_PATH = uc.find_chrome_executable()
    return CHROME_EXE_PATH

def _start_browser():
    global driver, USER_AGENT

    if driver != None:
        driver.quit()
        driver = None

    _start_xvfb_display()

    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-zygote')
    options.add_argument('--disable-gpu-sandbox')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--use-gl=swiftshader')
    if USER_AGENT is not None:
        options.add_argument('--user-agent=%s' % USER_AGENT)
    language = os.environ.get('LANG', None)
    if language is not None:
        options.add_argument('--lang=%s' % language)
    options.add_argument(' --disable-web-security')

    driver = uc.Chrome(options=options, headless=False, version_main=None, driver_executable_path="/app/chromedriver", browser_executable_path=get_chrome_exe_path())

    if USER_AGENT is None:
        USER_AGENT = driver.execute_script("return navigator.userAgent")
        USER_AGENT = re.sub('HEADLESS', '', USER_AGENT, flags=re.IGNORECASE)
        app.logger.info(USER_AGENT)

        driver.quit()
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-zygote')
        options.add_argument('--disable-gpu-sandbox')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--use-gl=swiftshader')
        if USER_AGENT is not None:
            options.add_argument('--user-agent=%s' % USER_AGENT)
        language = os.environ.get('LANG', None)
        if language is not None:
            options.add_argument('--lang=%s' % language)
        options.add_argument(' --disable-web-security')

        driver = uc.Chrome(options=options, headless=False, version_main=None, driver_executable_path="/app/chromedriver", browser_executable_path=get_chrome_exe_path())

    _reset_stop_timer()

    app.logger.info("browser started")

def _stop_browser():
    global driver
    driver.quit()
    driver = None
    app.logger.info("browser stopped")

def _reset_stop_timer():
    global timer
    if timer is not None:
        timer.cancel()
    timer = Timer(5*60, _stop_browser)
    timer.start()

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/start_browser")
def start_browser():
    _start_browser()
    return "ok"

@app.route("/close_browser")
def stop_browser():
    _stop_browser()
    return "ok"

@app.route("/text")
def text():
    global driver
    if driver == None:
        _start_browser()
    else:
        _reset_stop_timer()

    url =  request.args.get('url', '')
    driver.get(url)
    text = driver.page_source
    return text

@app.route("/screenshot")
def screenshot():
    global driver
    if driver is None:
        _start_browser()
    else:
        _reset_stop_timer()

    url = request.args.get('url', 'https://www.youtube.com')
    driver.get(url)
    
    time.sleep(5)  # Adjust the sleep time as needed

    screenshot_path = "/tmp/screenshot.png"
    driver.save_screenshot(screenshot_path)
    
    return send_file(screenshot_path, mimetype='image/png')

@app.route("/evaluate")
def evaluate():
    return "todo"

@app.route("/fetch")
def fetch():
    global driver
    if driver == None:
        _start_browser()
    else:
        _reset_stop_timer()

    url =  request.args.get('url', '')

    driver.get('https://i-invdn-com.investing.com/redesign/images/seo/investing_300X300.png')
    
    script = """
    var callback = arguments[arguments.length - 1];
    (async function(){
        try {
            let res = await fetch('%s', {headers:{'domain-id':'www'}});
            let text = await res.text();
            callback(text);
        } catch (e) {
            callback('error: ' + e);
        }
    })()""" % (url)
    result = driver.execute_async_script(script)
    return result

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=7860, debug=True)
