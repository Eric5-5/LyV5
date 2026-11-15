# 用 GitHub Actions 构建 APK —— 操作说明

这个目录里只有两个文件，**就是你要放进 GitHub 仓库的全部内容**：

```
.github/workflows/build-apk.yml   ← 构建流水线
patch_source.py                   ← 给上游引擎打移植补丁的脚本
```

为什么不在仓库里放整份安卓工程？因为 GitHub 网页上传**单次最多 100 个文件**，
而完整工程有 294 个文件、7.8 MB。所以这里改成「CI 自己去拉上游引擎 + 现场打补丁」，
你只需要传 2 个文件。

CI 做的事情：

1. 拉取上游 `BookerRues9/mkxp-z-android-reworked`（固定 commit `b668e08`，不会漂移）
2. 运行 `patch_source.py` 打 6 处移植补丁（触摸 / 关手柄层 / 去联网权限 / 应用名 / ABI / 版本号）
3. 在线拉取 SDL2、Ruby 3.1、OpenSSL 等依赖并交叉编译（arm64-v8a）
4. `gradlew assembleDebug` 产出 **debug 签名、可直接安装**的 APK
5. 上传为构建产物 `luoye-v5-apk`

---

## 步骤（全程浏览器，约 10 分钟操作 + 30~60 分钟等编译）

### 1. 建仓库

打开 <https://github.com/new>：

- Repository name：随意，例如 `luoye-v5`
- 选 **Private**（私有也可以，Actions 免费额度 2000 分钟/月，够用）或 Public
- 勾选 **Add a README file**（必须勾，否则仓库是空的、传不了文件）
- 点 **Create repository**

### 2. 上传两个文件

先把交付的 `挂机新落叶V5-github-builder.zip` 解压（得到 `README-使用说明.md`、`patch_source.py`、`.github\` 文件夹）。

在仓库首页点 **Add file → Upload files**，把解压出来的：

- 文件夹 `.github`（连同里面的 `workflows\build-apk.yml`）
- 文件 `patch_source.py`

一起拖进网页（资源管理器里 `Ctrl+A` 全选这两项拖进去即可，拖文件夹会自动保留路径）。
等文件列表出现 `.github/workflows/build-apk.yml` 和 `patch_source.py` 两行后，点 **Commit changes**。

> 注意：`.github` 这一层目录结构必须保留，否则 GitHub 不会识别流水线。
> 如果拖拽后网页里显示的是 `build-apk.yml` 直接在根目录，说明目录结构丢了 ——
> 改用「Add file → Create new file」，文件名填 `.github/workflows/build-apk.yml`，
> 再把文件内容粘进去。

### 3. 运行流水线

1. 打开仓库顶部的 **Actions** 标签；
2. 如果提示工作流未启用，点 **I understand my workflows, go ahead and enable them**；
3. 左侧选 **Build 挂机新落叶V5 APK** → 右侧 **Run workflow** → **Run workflow**；
4. 刷新页面，会出现一条运行记录，点进去看实时日志。

> 往 main 分支 push 也会自动触发，所以第 2 步 commit 后可能已经自动跑起来了，直接用那次即可。

### 4. 下载 APK

运行记录页面底部 **Artifacts** → 下载 `luoye-v5-apk`（一个 zip），
解压得到 `app-arm64-v8a-debug.apk`（或 `app-universal-debug.apk`）。

传到手机安装即可（首次需允许「安装未知来源应用」）。

---

## 装好 APK 之后：拷贝游戏数据

APK 只是引擎，游戏本体要放到手机存储：

```
把「挂机新落叶V5-game.zip」解压后的全部内容放到：
/storage/emulated/0/mkxp-z/
```

正确结构应该是：

```
/storage/emulated/0/mkxp-z/Game.ini
/storage/emulated/0/mkxp-z/mkxp.json
/storage/emulated/0/mkxp-z/Data/Scripts.rxdata
/storage/emulated/0/mkxp-z/Graphics/...
/storage/emulated/0/mkxp-z/BJ/...
/storage/emulated/0/mkxp-z/Fonts/wqymicrohei.ttf
/storage/emulated/0/mkxp-z/preload/000_compat.rb
```

先建好这个目录再开 App。打开后授予「所有文件访问权限」（Android 11+ 必需，存档要写这里）→ 进入游戏。
800×600、4:3 横屏，**触摸 = 鼠标点击**。没有触摸时也会自动退化为「方向键移动光标 + 回车点击」。

---

## 排错

| 现象 | 原因 / 处理 |
|---|---|
| APK 装不上，提示「不兼容」 | 手机是 32 位（armeabi-v7a）。当前只编了 arm64-v8a，把手机型号发我，我加 armv7 |
| 打开提示 Failed to set current directory | 手机里没有 `/storage/emulated/0/mkxp-z/` 这个目录，或路径不对 |
| 打开黑屏/闪退 | 先确认目录里有 `Game.ini` 和 `Data/Scripts.rxdata`；再看是否给了「所有文件访问」 |
| 进游戏但点不动 | 先用方向键移动、回车点击（虚拟光标模式）确认游戏本身正常；若光标能动但触摸无效，说明触摸补丁没生效，把日志发我 |
| 中文是方块 | `Fonts/wqymicrohei.ttf` 没拷进去，或 `mkxp.json` 没跟着拷 |
| 构建失败在 make 阶段 | 把日志里第一条 `error:` 发我 |
| 构建失败在 patch_source.py | 理论上不会（已固定上游 commit）；把报错发我 |
