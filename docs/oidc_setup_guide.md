# AWS OIDC Setup Guide for GitHub Actions

To remove hardcoded secrets, follow these steps to create a Trust Relationship between AWS and your GitHub Repo.

## 1. Create Identity Provider (If not exists)
1. Go to **AWS IAM Console** > **Identity providers**.
2. Click **Add provider**.
3. Select **OpenID Connect**.
   - **Provider URL**: `https://token.actions.githubusercontent.com`
   - **Audience**: `sts.amazonaws.com`
4. Click **Add provider**.

## 2. Create IAM Role
1. Go to **Roles** > **Create role**.
2. Select **Web identity**.
3. Choose the provider you just created (`token.actions.githubusercontent.com`).
4. Select Audience `sts.amazonaws.com`.
5. Click **Next** > **Next** (Skip permissions for now).
6. Name the role: `GitHubActions-AgriPrice-Role`.
7. Click **Create role**.

## 3. Configure Trust Policy
1. Open the newly created role (`GitHubActions-AgriPrice-Role`).
2. Go to **Trust relationships** tab > **Edit trust policy**.
3. Paste the following JSON (Replace `[YOUR_AWS_ACCOUNT_ID]` with your 12-digit ID):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::[YOUR_AWS_ACCOUNT_ID]:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:cryl-z/Agri-Price-Intelligence-Platform:*"
                },
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                }
            }
        }
    ]
}
```

## 4. Add Permissions
1. Go to **Permissions** tab > **Add permissions** > **Create inline policy**.
2. Select **S3**.
3. Check **ListBucket** and **PutObject** (or `s3:*` if you want full control for now).
4. Specify your bucket ARN (`arn:aws:s3:::apip-data-lake-2026-crylz/*`).
5. Name it `S3AccessPolicy` and create.

## 5. Get Role ARN
1. Copy the **ARN** from the Role summary (e.g., `arn:aws:iam::123456789012:role/GitHubActions-AgriPrice-Role`).
2. You will provide this to the `daily_run.yml` file.
