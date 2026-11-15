#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 CI 里对上游 mkxp-z-android 工程打「挂机新落叶V5」移植补丁。

为什么不在仓库里放整份工程：
  GitHub 网页上传单次最多 100 个文件，而上游工程有 294 个文件。
  所以仓库只放本脚本 + workflow，由 CI 拉取上游（固定 commit）后再打补丁。

补丁内容：
  1. eventthread.cpp  —— 保留 SDL 把触摸合成的鼠标事件（触摸 = 点击）
  2. MainActivity.java —— 关闭屏幕手柄覆盖层（会遮挡/吞掉点击）
  3. AndroidManifest.xml —— 删除联网权限（纯单机）
  4. strings.xml —— 应用名改为「挂机新落叶V5」
  5. Application.mk —— 只编 arm64-v8a（CI 只构建该 ABI 的原生依赖）
  6. app/build.gradle —— 只打 arm64-v8a 包，版本号改为 1.0.0-port

用法: python3 patch_source.py <上游工程根目录>
"""
import os
import sys

PATCHES = []


def add(path, old, new, note):
    PATCHES.append((path, old, new, note))


add(
    'app/jni/mkxp-z/src/eventthread.cpp',
    """\t\t\tcase SDL_MOUSEBUTTONDOWN:
\t\t\tcase SDL_MOUSEBUTTONUP:
\t\t\tcase SDL_MOUSEMOTION:
\t\t\t\tif (event.button.which == SDL_TOUCH_MOUSEID)
\t\t\t\t\tcontinue;
\t\t\t\tbreak;""",
    """\t\t\tcase SDL_MOUSEBUTTONDOWN:
\t\t\tcase SDL_MOUSEBUTTONUP:
\t\t\tcase SDL_MOUSEMOTION:
\t\t\t\t/* 挂机新落叶V5 安卓移植：不再丢弃触摸合成的鼠标事件。
\t\t\t\t * 本作全靠鼠标点 UI，触摸必须等价于点鼠标：
\t\t\t\t * 保留 which == SDL_TOUCH_MOUSEID 的事件后，
\t\t\t\t * Input.mouse_x / mouse_y 与 MOUSELEFT 才能在安卓上生效。 */
\t\t\t\tbreak;""",
    '触摸合成鼠标事件不再丢弃')

add(
    'app/src/main/java/com/hatkid/mkxpz/MainActivity.java',
    """        // Setup in-screen gamepad
        mGamepadInvisible = (isAndroidTV() || isChromebook());
        GamepadConfig gpadConfig = new GamepadConfig();
        mGamepad.init(gpadConfig, mGamepadInvisible);
        mGamepad.setOnKeyDownListener(SDLActivity::onNativeKeyDown);
        mGamepad.setOnKeyUpListener(SDLActivity::onNativeKeyUp);

        if (mLayout != null) {
            mGamepad.attachTo(this, mLayout);
        }""",
    """        // 挂机新落叶V5 安卓移植：本作是鼠标/触摸操作（点哪打哪），
        // 屏幕手柄覆盖层会遮挡并吞掉点击区域，因此恒定为隐藏、不挂载。
        mGamepadInvisible = true;""",
    '关闭屏幕手柄覆盖层')

add(
    'app/src/main/java/com/hatkid/mkxpz/MainActivity.java',
    """    @Override
    public boolean dispatchTouchEvent(MotionEvent evt)
    {
        // Show gamepad view on touch when hidden
        if (mGamepadInvisible) {
            mGamepad.showView();
            mGamepadInvisible = false;
        }

        return super.dispatchTouchEvent(evt);
    }""",
    """    @Override
    public boolean dispatchTouchEvent(MotionEvent evt)
    {
        // 触摸事件直接交给 SDL → mkxp（native 侧已打补丁：触摸合成鼠标）
        return super.dispatchTouchEvent(evt);
    }""",
    '触摸直通 SDL')

add(
    'app/src/main/AndroidManifest.xml',
    """    <!-- Access to internet -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />""",
    """    <!-- 挂机新落叶V5 安卓移植：纯单机，删除联网权限 -->
    <!-- <uses-permission android:name="android.permission.INTERNET" /> -->
    <!-- <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" /> -->""",
    '删除联网权限')

add(
    'app/src/main/res/values/strings.xml',
    '<string name="app_name">mkxp-z</string>',
    '<string name="app_name">挂机新落叶V5</string>',
    '应用名')

add(
    'app/jni/Application.mk',
    'APP_ABI := arm64-v8a armeabi-v7a',
    'APP_ABI := arm64-v8a',
    '只编 arm64-v8a')

add(
    'app/build.gradle',
    "            include 'arm64-v8a', 'armeabi-v7a'",
    "            include 'arm64-v8a'",
    '只打 arm64-v8a')

add(
    'app/build.gradle',
    '''        versionCode 11
        versionName "0.1.1"''',
    '''        versionCode 12
        versionName "1.0.0-port"''',
    '版本号')


def main():
    if len(sys.argv) < 2:
        print('usage: python3 patch_source.py <engine-root>')
        return 2
    root = sys.argv[1]
    if not os.path.isdir(root):
        print('!! not a directory: %s' % root)
        return 2

    # 同一个文件可能有多处补丁：在内存里串行修改，最后统一落盘
    cache = {}
    crlf = {}
    changed = set()

    def load(rel):
        if rel not in cache:
            with open(os.path.join(root, rel), 'r', encoding='utf-8', newline='') as f:
                text = f.read()
            crlf[rel] = '\r\n' in text
            cache[rel] = text.replace('\r\n', '\n')
        return cache[rel]

    for rel, old, new, note in PATCHES:
        if not os.path.isfile(os.path.join(root, rel)):
            print('!! MISSING FILE %s' % rel)
            return 1
        text = load(rel)
        marker = new.split('\n')[0]
        if marker and marker in text and old not in text:
            print('[skip] %-44s (%s)' % (rel, note))
            continue
        if old not in text:
            print('!! ANCHOR NOT FOUND in %s (%s)' % (rel, note))
            print('   upstream may have changed; update patch_source.py')
            return 1
        cache[rel] = text.replace(old, new, 1)
        changed.add(rel)
        print('[ ok ] %-44s (%s)' % (rel, note))

    for rel in sorted(changed):
        text = cache[rel]
        if crlf[rel]:
            text = text.replace('\n', '\r\n')
        with open(os.path.join(root, rel), 'w', encoding='utf-8', newline='') as f:
            f.write(text)
    print('patched %d file(s)' % len(changed))
    return 0


if __name__ == '__main__':
    sys.exit(main())
