#!/bin/bash

# AI Fitness Coach Lite - GitHub Repository Setup Script
# 
# Before running this script:
# 1. Create a new repository on GitHub named 'ai-fitness-coach-lite'
# 2. Replace YOUR_USERNAME below with your actual GitHub username
# 3. Run this script from the project root directory

echo "🚀 Setting up AI Fitness Coach Lite GitHub Repository"
echo "================================================="

# Replace YOUR_USERNAME with your actual GitHub username
GITHUB_USERNAME="YOUR_USERNAME"
REPO_NAME="ai-fitness-coach-lite"

if [ "$GITHUB_USERNAME" = "YOUR_USERNAME" ]; then
    echo "❌ Please edit this script and replace YOUR_USERNAME with your actual GitHub username"
    exit 1
fi

echo "📂 Repository: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
echo ""

# Add remote origin
echo "🔗 Adding remote origin..."
git remote add origin "https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"

# Push to GitHub
echo "⬆️ Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Repository successfully created and pushed to GitHub!"
    echo "🌐 View your repository at: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Visit your repository on GitHub"
    echo "   2. Add a description and topics"
    echo "   3. Enable GitHub Pages (optional)"
    echo "   4. Set up branch protection rules (recommended)"
    echo "   5. Configure GitHub Actions for CI/CD (optional)"
else
    echo ""
    echo "❌ Failed to push to GitHub. Please check:"
    echo "   - Repository exists on GitHub"
    echo "   - You have push permissions"
    echo "   - Your GitHub credentials are configured"
fi