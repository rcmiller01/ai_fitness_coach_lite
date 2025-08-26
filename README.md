# AI Fitness Coach Lite 🏋️‍♂️

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A comprehensive, offline-capable AI fitness coaching platform with advanced plugin architecture, real-time pose analysis, and intelligent workout recommendations.

## 🌟 Features

### Core Platform
- **🎯 AI-Powered Workout Planning** - Personalized fitness routines based on user goals and capabilities
- **🎥 Real-time Pose Analysis** - Computer vision-based form correction using MediaPipe/BlazePose
- **🗣️ Voice Coaching** - Natural language feedback with edge-TTS integration
- **📊 Comprehensive Logging** - Detailed workout tracking and progress analytics
- **💾 Offline Capability** - Full functionality without internet connection

### Plugin Ecosystem
- **🔌 Modular Plugin Architecture** - Extensible sports-specific coaching modules
- **⛳ Golf Pro Plugin** - Swing analysis with tempo and plane correction
- **🎾 Tennis Pro Plugin** - Stroke analysis for serve, forehand, and backhand
- **🏀 Basketball Skills Plugin** - Shooting form and dribbling technique analysis
- **📱 Mobile Integration** - Native iOS/Android plugin support
- **💳 Plugin Store** - Marketplace with licensing and payment processing

### Production Infrastructure
- **🐳 Docker Deployment** - Complete containerization with Docker Compose
- **🗄️ Database Integration** - PostgreSQL with migration tools and JSON fallback
- **☁️ Cloud Storage** - Multi-provider support (AWS S3, Google Cloud, Azure)
- **💰 Payment Processing** - Stripe integration with webhook handling
- **📈 Monitoring & Analytics** - Real-time performance monitoring and user analytics
- **🧪 A/B Testing Framework** - Data-driven optimization with statistical analysis

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/ai-fitness-coach-lite.git
cd ai-fitness-coach-lite
```

2. **Set up environment**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

3. **Configure environment**
```bash
# Copy environment template
cp .env.example .env

# Edit configuration (database, API keys, etc.)
nano .env
```

4. **Run with Docker (Recommended)**
```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

5. **Or run locally**
```bash
# Start the API server
python main.py

# Access the application
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

## 📖 Documentation

- **[API Documentation](docs/api_documentation.md)** - Complete API reference
- **[Plugin Development Guide](docs/plugin_development_guide.md)** - Create custom sports modules
- **[A/B Testing Framework](docs/ab_testing_framework.md)** - Optimize user experience
- **[Deployment Guide](docs/deployment_guide.md)** - Production deployment instructions

## 🏗️ Architecture

```
ai_fitness_coach_lite/
├── core/                 # Core business logic
│   ├── health_parser.py     # Health data processing
│   ├── analytics.py         # User analytics system
│   ├── performance_monitor.py # Performance monitoring
│   └── ab_testing.py        # A/B testing framework
├── utils/                # Utility modules
│   ├── logger.py           # Workout logging
│   ├── voice_output.py     # TTS voice feedback
│   └── visual_aide.py      # Pose visualization
├── plugins/              # Plugin ecosystem
│   ├── core/               # Plugin architecture
│   ├── golf_pro/           # Golf swing analysis
│   ├── tennis_pro/         # Tennis stroke analysis
│   └── basketball_skills/  # Basketball form analysis
├── api/                  # FastAPI endpoints
│   ├── main.py             # API router
│   ├── analytics_api.py    # Analytics endpoints
│   └── ab_testing_api.py   # A/B testing endpoints
├── tests/                # Comprehensive test suite
├── scripts/              # Deployment & maintenance
├── docs/                 # Documentation
└── demos/                # Interactive demonstrations
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=. --cov-report=html

# Run specific test modules
python -m pytest tests/test_ab_testing.py -v
python -m pytest tests/test_analytics.py -v
python -m pytest tests/test_performance_monitor.py -v
```

## 🔧 Development

### Plugin Development

Create a new sports analysis plugin:

```python
from plugins.core.base_plugin import BasePlugin, PluginCapability

class MyPortPlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.capabilities = [
            PluginCapability.POSE_ANALYSIS,
            PluginCapability.VOICE_FEEDBACK
        ]
    
    def analyze_movement(self, pose_data):
        # Implement sport-specific analysis
        return {
            "form_score": 85,
            "feedback": "Great technique!",
            "corrections": []
        }
```

### API Integration

Use the REST API for frontend/mobile integration:

```python
import requests

# Get user recommendations
response = requests.get(f"/api/ab-testing/users/{user_id}/plugin-recommendations")
recommendations = response.json()

# Track user events
requests.post(f"/api/ab-testing/users/{user_id}/experiments/{exp_id}/events", json={
    "metric_id": "plugin_download_rate",
    "event_type": "plugin_download",
    "event_value": 1.0
})
```

## 📊 Monitoring & Analytics

### Performance Monitoring
- Real-time system metrics with Prometheus integration
- Automated alerting for performance degradation
- Error tracking with contextual information

### User Analytics
- Comprehensive user behavior tracking
- Plugin usage analytics and conversion metrics
- Custom event tracking for business insights

### A/B Testing
- Statistical experiment framework
- Plugin recommendation optimization
- Feature flag integration for progressive rollouts

## 🚀 Deployment

### Docker Deployment (Recommended)

```bash
# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Scale services
docker-compose up -d --scale api=3

# Monitor logs
docker-compose logs -f
```

### Cloud Deployment

The platform supports deployment on:
- **AWS** - ECS/EKS with RDS and S3
- **Google Cloud** - GKE with Cloud SQL and Cloud Storage
- **Azure** - AKS with Azure Database and Blob Storage

See [Deployment Guide](docs/deployment_guide.md) for detailed instructions.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `python -m pytest`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📋 Roadmap

### Version 2.0 (Planned)
- [ ] Advanced ML models for pose correction
- [ ] Real-time multiplayer workouts
- [ ] Nutrition tracking integration
- [ ] Wearable device integration (Apple Watch, Fitbit)
- [ ] Social features and community challenges

### Version 2.1 (Future)
- [ ] AR/VR workout experiences
- [ ] Advanced biometric analysis
- [ ] AI personal trainer conversations
- [ ] Integration with gym equipment

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **MediaPipe** - Real-time pose detection
- **FastAPI** - Modern web framework
- **Docker** - Containerization platform
- **PostgreSQL** - Robust database system
- **Stripe** - Payment processing
- **Edge-TTS** - Text-to-speech synthesis

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/ai-fitness-coach-lite/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/ai-fitness-coach-lite/discussions)

---

**AI Fitness Coach Lite** - Empowering fitness through AI technology 🚀

Built with ❤️ by the AI Fitness Coach Team