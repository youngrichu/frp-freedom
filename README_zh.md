# FRP Freedom - Android FRP 绕过工具（中文版）

FRP Freedom 是一款合法的安卓出厂重置保护（FRP）绕过工具，专为合法设备拥有者设计的设备恢复。该工具为用户在失去 Google 帐户访问权限或遗忘凭证时，提供了绕过 FRP 锁的全面解决方案。

## ⚠️ 重要法律通知
该工具仅供合法设备所有者进行合法设备恢复目的。用户需完全负责确保其使用符合适用法律法规。

- ✅ 合法使用：忘记 Google 帐户凭证后找回自己的设备
- ✅ 授权使用：帮助员工处理公司设备的 IT 支持
- ✅ 合法用途：拥有适当客户授权的维修店
- ❌ 非法使用：绕过被盗或未经授权设备的 FRP
- ❌ 禁止：任何违反当地法律或法规的使用

## 🌟 特色
- 核心绕过方法：ADB 漏洞、界面漏洞、系统漏洞、硬件漏洞
- 安全与伦理：审计跟踪、速率限制、本地处理
- 用户体验：向导界面、设备检测、智能推荐、进展跟踪
- 智能功能：设备分析、方法推荐、性能跟踪、上下文帮助

## 兼容性
- Android 版本：5.0（API 21）至 15.0（API 35）
- 主要 OEM 厂商：三星、谷歌、华为、小米、一加、LG、索尼、摩托罗拉
- 平台：Windows、macOS、Linux

## 📋 快速入门
详细的设置说明请参见 `SETUP_GUIDE.md`。

### 选项一：从源码（开发）
```bash
git clone https://github.com/youngrichu/frp-freedom.git
cd frp-freedom
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 选项二：独立可执行文件（即将推出）
预构建的可执行文件将可从发布页面下载。

## 使用指南（概览）
1. 启动应用：`python main.py`
2. 连接设备：启用 USB 调试 → 通过 USB 线连接设备
3. 选择方法：查看推荐方法并选择
4. 执行并监控：实时查看进度与日志

> 详细的工作流程、配置说明、测试与开发信息请参见项目仓库中的 `README.md`（英文）及 `SETUP_GUIDE.md`。

## 🛠️ 开发与测试
- 克隆并安装依赖：`pip install -r requirements.txt`
- 运行测试：`pytest tests/`
- 代码风格：`black src/`，`flake8 src/`

---

**免责声明**：本软件仅供教育与合法设备恢复目的使用。开发者不对本软件的滥用或由此产生的任何法律后果承担责任。