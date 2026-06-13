# Android 云端打包说明

本项目已经准备了以下安卓打包基础文件：

- `buildozer.spec`
- `.github/workflows/android-apk.yml`
- `assets/icon/icon_512.png`
- `assets/icon/presplash.png`

## 一、推荐方式

推荐使用 `GitHub Actions` 云端打包，不在本机安装安卓环境。

## 二、使用步骤

1. 把当前项目上传到 GitHub 仓库。
2. 打开 GitHub 仓库页面。
3. 进入 `Actions`。
4. 找到工作流 `Android APK`。
5. 点击 `Run workflow`。
6. 等待构建完成。
7. 在工作流产物里下载 `android-build-artifacts`。
8. 下载得到的 `bin/*.apk` 即可安装测试。

## 三、当前配置说明

- 应用标题：`斗兽棋`
- 包名：`com.huyouchao.doushouqi`
- 最低安卓版本：`Android 8.0 (API 26)`
- 屏幕方向：`all`
  说明：当前配置为横竖屏都允许，后续如果你决定只保留横屏主体验，也可以再改。
- CPU 架构：`arm64-v8a, armeabi-v7a`

## 四、当前已知注意事项

1. 当前内置字体 `assets/fonts/msyh.ttc` 是开发过渡方案。
   如果后续要对外发布，建议替换为可再分发的开源中文字体。

2. 当前 GitHub Actions 工作流属于“第一版可执行骨架”。
   真正首次云端打包时，如果构建日志提示某些 Linux 依赖、NDK 或 API 版本需要微调，需要根据日志继续调整。

3. 当前代码已经补了安卓方向的这些基础适配：
   - 应用内存档读写弹窗
   - 数据目录统一
   - 响应式布局基础层
   - 安卓返回键基础处理
   - 软键盘遮挡缓解

4. 当前还没有做真实安卓真机构建验证。
   所以正式 APK 成功产出前，仍然可能需要 1 到 2 轮工作流参数微调。

## 五、如果工作流失败，优先看哪里

1. `buildozer.spec`
2. GitHub Actions 构建日志
3. Python 依赖和安卓 API/NDK 版本提示
4. 字体、图标、资源文件路径是否存在

## 六、后续建议

首次云端打包成功后，建议马上做这几件事：

1. 用安卓手机安装 APK。
2. 测试登录、对局、存档、读档、积分、返回键。
3. 测试横屏和竖屏切换。
4. 再根据真机效果继续调界面。
