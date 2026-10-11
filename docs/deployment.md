# Ubuntu + Nginx + GitHub Actions 部署

工作流位于 `.github/workflows/deploy.yml`：PR 到 `main` 时检查站点；推送到 `main` 时检查并部署；也可以在 Actions 中手动运行 `Website CI/CD`（选择 `main`）。

检查内容包括 HTML/CSS/公共组件的本地资源路径、必要的 JSON 数据文件、JSON 格式及 JavaScript 语法。只发布根目录的 HTML 和 `css/`、`js/`、`images/`、`data/`，另生成 `deploy-version.txt` 用于验证本次提交已由 Nginx 提供。

## 1. 准备服务器目录

以下命令在服务器的 `ubuntu` 用户下执行。如果你使用其他 SSH 用户，把 `ubuntu:ubuntu` 换成相应的用户和组。

```bash
sudo apt update
sudo apt install -y rsync curl
sudo mkdir -p /var/www/acmwebsite
sudo chown -R ubuntu:ubuntu /var/www/acmwebsite
sudo chmod -R u+rwX,go+rX /var/www/acmwebsite
```

这是本项目的专用发布目录。自动同步会删除其中已从仓库移除的文件，并保留 `.well-known/`；不要在该目录存放其他网站或手动维护的数据。服务器上的 `~/acmwebsite` Git 仓库可以保留，但 CI/CD 直接同步已检查的文件到发布目录。

Nginx 的静态站点 `root` 应为 `/var/www/acmwebsite`。沿用已有配置时，访问路径为：

```text
二级域名 → 已有 Nginx（80/443）→ 127.0.0.1:8081 → /var/www/acmwebsite
```

先在服务器确认后端正常：

```bash
curl -I http://127.0.0.1:8081/
```

8081 仅监听本机，不需要在安全组开放。工作流通过 SSH 连接服务器，因此服务器的 SSH 端口必须允许 GitHub 托管 runner 连接。部署文件时不需要 sudo 或重启 Nginx。

## 2. 创建专用 SSH 密钥

在本机 Windows PowerShell 中执行（密钥放在用户目录，不放进项目）：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh" | Out-Null
ssh-keygen -t ed25519 -C "github-actions-sspuacm" -f "$env:USERPROFILE\.ssh\sspuacm_actions"
Get-Content "$env:USERPROFILE\.ssh\sspuacm_actions.pub"
```

创建密钥时，密码提示两次直接回车，使用无密码的部署密钥。如果这个文件名已存在，使用新名字，保留原来的密钥。

复制输出的整行公钥。在服务器的 SSH 登录用户（例如 `ubuntu`）下执行：

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
nano ~/.ssh/authorized_keys
```

将公钥追加为新的一行，保存退出，再执行：

```bash
chmod 600 ~/.ssh/authorized_keys
```

保留 `authorized_keys` 中已有的登录公钥。

## 3. 记录服务器主机公钥

在服务器执行，记录指纹：

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

在本机 PowerShell 执行，将 `服务器IP` 换成公网 IP。如果 SSH 端口不是 22，替换 `-p 22`：

```powershell
ssh-keyscan -t ed25519 -p 22 服务器IP 2>$null | Set-Content -Encoding ascii "$env:USERPROFILE\.ssh\sspuacm_known_hosts"
ssh-keygen -lf "$env:USERPROFILE\.ssh\sspuacm_known_hosts"
```

确认两处 SHA256 指纹一致，再复制 `sspuacm_known_hosts` 文件的内容。工作流严格校验该主机公钥。`SSH_HOST` 使用的 IP/主机名必须和扫描时一致；非 22 端口的记录形如 `[服务器IP]:端口 ssh-ed25519 ...`。

## 4. 设置 GitHub Secrets

进入仓库 **Settings → Secrets and variables → Actions → New repository secret**，创建：

| 名称 | 内容 |
| --- | --- |
| `SSH_HOST` | 服务器公网 IP 或 SSH 主机名，不带协议、用户名或端口 |
| `SSH_USER` | `ubuntu`，或实际配置公钥且拥有发布目录写权限的用户 |
| `SSH_PRIVATE_KEY` | 本机 `sspuacm_actions` 私钥的完整内容，包含 BEGIN/END 两行 |
| `SSH_KNOWN_HOSTS` | 上一步已核对指纹的 `sspuacm_known_hosts` 文件内容 |
| `SSH_PORT` | 可选，SSH 端口，默认 `22`；与网站的 80/8081 端口不同 |

在 PowerShell 中可将私钥直接复制到剪贴板，再粘贴到 GitHub Secret：

```powershell
Get-Content -Raw "$env:USERPROFILE\.ssh\sspuacm_actions" | Set-Clipboard
```

私钥只填入 GitHub Secrets，不提交到仓库，也不粘贴到聊天中。

工作流默认在服务器上请求 `http://127.0.0.1:8081/deploy-version.txt`，检查返回的提交 SHA。若你的后端端口不同，在 **Actions → Variables → New repository variable** 中设置 `SITE_CHECK_URL`，例如 `http://127.0.0.1:8080`。该地址不包含 `deploy-version.txt`；如果改用域名，可填写 `https://acm.example.com`。

## 5. 首次运行和日常更新

先完成服务器、公钥和 Secrets 的配置，再提交并推送工作流：

```bash
git add .github/workflows/deploy.yml scripts/check_site.py docs/deployment.md README.md
git commit -m "ci: add website validation and SSH deployment"
git push origin main
```

在 GitHub 的 **Actions → Website CI/CD** 查看执行结果。检查成功后才会部署；上传前确认 Nginx 的 HTTP 端口可连接，部署完成后会验证 Nginx 返回的版本。手动运行时选择 `main`，其他分支只检查。

同步日志会显示传输进度和统计；rsync 按文件内容校验跳过未变化的文件，避免 GitHub checkout 和解压后的修改时间导致重复同步。连续 120 秒没有传输数据时会退出并报告错误。

以后修改网站、提交并推送到 `main` 即可自动发布，服务器不需要再手动 `git pull`。

本地检查：

```bash
python scripts/check_site.py
```

需要 Python 3 和 Node.js，无额外 Python/Node 包依赖。

## 常见问题

- `Missing repository secret`：按报错名称补充仓库 Secret。
- `Permission denied (publickey)`：核对 SSH 用户、无密码私钥，以及该用户 `authorized_keys` 中的公钥；云服务器可能还有 SSH 访问限制。
- `Host key verification failed`：核对 `SSH_HOST`、`SSH_PORT` 和主机公钥，重新比较指纹后更新 `SSH_KNOWN_HOSTS`。
- rsync 写入或删除失败：检查发布目录及其中已有文件是否都属于部署用户；再次执行第 1 步的权限命令。
- `Cannot connect to Nginx` 或 `Connection refused`：服务器未监听 `SITE_CHECK_URL` 指定的端口。在服务器运行 `sudo ss -ltnp` 检查；启用网站的 Nginx 配置，或把仓库变量 `SITE_CHECK_URL` 改为实际地址后重新运行工作流。
- 版本验证失败：文件可能已同步，但 Nginx 的 `root`、后端端口或 `SITE_CHECK_URL` 不匹配；修正后重新运行工作流。检查失败不会自动回滚，rsync 的延迟更新也不是整个站点的原子切换。
- CI 报本地资源缺失：核对路径及文件名大小写，Linux 区分大小写。

参考：[GitHub 工作流语法](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)、[GitHub Secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)。
