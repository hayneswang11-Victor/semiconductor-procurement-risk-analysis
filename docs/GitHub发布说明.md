# GitHub 发布说明

## 推荐仓库名

`semiconductor-procurement-risk-analysis`

## 推荐中文描述

`半导体与制造业采购成本、需求与供应风险分析｜Python + Excel｜含 EDA/IP 授权采购扩展`

## 推荐 Topics

- procurement
- supply-chain
- sourcing
- semiconductor
- python
- excel
- monte-carlo
- risk-analysis
- eda

## Windows PowerShell 发布流程

将本交付包解压到本地 GitHub 目录后：

```powershell
cd "E:\My GitHub\semiconductor-procurement-risk-analysis"

git init
git add .
git commit -m "Initial release: procurement cost and supply risk analysis"
git branch -M main
git remote add origin <你的GitHub仓库URL>
git push -u origin main
```

## 发布前检查

1. README 首页是否为中文；
2. Excel、报告能否正常打开；
3. `data/` 中无真实企业或个人敏感数据；
4. 不上传本地缓存、虚拟环境或 Office 临时文件；
5. GitHub 仓库说明中继续保留“模拟数据”边界。
