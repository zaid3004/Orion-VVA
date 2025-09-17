# 🤖 Orion VVA - Voice Virtual Assistant

<div align="center">

![Orion VVA](https://img.shields.io/badge/Orion-VVA-0047AB?style=for-the-badge&logo=robot&logoColor=white)
![Version](https://img.shields.io/badge/version-2.0-brightgreen?style=for-the-badge)
![AI Powered](https://img.shields.io/badge/AI-GROQ_Powered-red?style=for-the-badge)
![Analytics](https://img.shields.io/badge/Analytics-Enabled-gold?style=for-the-badge)

**Professional Voice Assistant with Optimus Prime Personality**

[🚀 Live Demo](https://orion-qjz84edl3-zaid-shaheeds-projects.vercel.app) | [📊 Analytics Guide](ANALYTICS_SETUP.md) | [🔧 Setup Guide](vercel-env-setup.md)

</div>

---

## 🌟 Features

### 🎤 **Voice Intelligence**
- **AI-Powered Responses** - GROQ LLaMA integration for natural conversations
- **Voice Commands** - Natural language processing with 90%+ accuracy
- **Male Leadership Voice** - Deep, commanding Optimus Prime-inspired speech synthesis
- **Wake Word Detection** - "Hey Orion" activation with continuous listening

### ⏰ **Advanced Timer System**
- **Analog Clocks** - Beautiful rotating hands showing real-time progress
- **Digital Countdown** - Large, readable time display
- **Multi-Timer Support** - Run multiple timers simultaneously
- **Smart Notifications** - Voice, sound, and browser alerts on completion
- **Natural Commands** - "Set timer for 5 minutes", "30 second timer"

### 🎨 **Optimus Prime Design**
- **Authentic Colors** - Deep cobalt blue (#0047AB), red (#cc0000), gold (#ffd700)
- **Military Styling** - Command interface with strategic elements
- **3-Part Layout** - Mission Communications | Timers | System Intelligence
- **Theme System** - Orion (default), Dark, Light modes
- **Responsive Design** - Works on desktop, tablet, and mobile

### 🔐 **User Management**
- **Secure Authentication** - JWT-based login/register system
- **MongoDB Integration** - User profiles and conversation storage
- **Session Management** - Persistent login with secure tokens
- **User Profiles** - Customizable settings and preferences

### 📊 **Enterprise Analytics**
- **Vercel Analytics** - Performance and traffic monitoring
- **Google Analytics 4** - User behavior and conversion tracking
- **Custom Events** - Voice command usage, timer operations, errors
- **Real-time Monitoring** - Live event tracking in console and logs
- **Error Tracking** - Comprehensive debugging and monitoring

## 🛠️ Technology Stack

### Frontend
- **HTML5** - Semantic structure with accessibility
- **CSS3** - Advanced animations and responsive design
- **JavaScript ES6+** - Modern async/await, classes, modules
- **Web Speech API** - Voice recognition and synthesis
- **Font Awesome** - Professional iconography

### Backend
- **Python/Flask** - Lightweight, scalable REST API
- **MongoDB Atlas** - Cloud database with indexing
- **GROQ AI** - LLaMA 3.3 70B language model
- **JWT Authentication** - Secure token-based auth
- **BCrypt** - Password hashing and security

### Analytics & Monitoring
- **Vercel Analytics** - Built-in performance tracking
- **Google Analytics 4** - Advanced user behavior analysis
- **Custom Analytics** - Voice-specific event tracking
- **Error Monitoring** - JavaScript error tracking and reporting

### Deployment
- **Vercel** - Serverless deployment platform
- **GitHub Actions** - CI/CD pipeline
- **Environment Variables** - Secure configuration management
- **CDN** - Global content delivery

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- MongoDB Atlas account
- GROQ API key
- Vercel account

### Local Development

1. **Clone Repository**
```bash
git clone https://github.com/zaid3004/Orion-VVA.git
cd Orion-VVA
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
npm install
```

3. **Environment Setup**
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. **Run Development Server**
```bash
python api/orion.py
```

5. **Access Application**
```
http://localhost:5000
```

### Production Deployment

1. **Deploy to Vercel**
```bash
vercel --prod
```

2. **Set Environment Variables**
- Add GROQ_API_KEY, MONGODB_URI, SECRET_KEY in Vercel dashboard

3. **Enable Analytics**
- Vercel Analytics: Automatic
- Google Analytics: Add tracking ID to HTML

## 📋 Environment Variables

Create a `.env` file with:

```env
# AI Integration
GROQ_API_KEY=your_groq_api_key_here

# Database
MONGODB_URI=your_mongodb_connection_string

# Security
SECRET_KEY=your_secret_key_for_jwt_tokens

# Optional
OPENWEATHER_API_KEY=your_weather_api_key
```

## 🎯 Usage Examples

### Voice Commands
```
"Hey Orion, set a timer for 5 minutes"
"What time is it?"
"Tell me a joke"
"How's the weather?"
"Set a 30 second timer"
"What can you do?"
```

### API Endpoints
```bash
# Health Check
GET /health

# Process Voice Command
POST /api/process-command
{
  "command": "set timer for 2 minutes"
}

# Get Analytics
POST /api/analytics
{
  "event_name": "custom_event",
  "properties": {"key": "value"}
}

# User Authentication
POST /api/auth/login
POST /api/auth/register
```

## 📊 Analytics Dashboard

### Tracked Events
- **Voice Commands** - Type, success rate, processing time
- **Timer Usage** - Creation, completion, duration patterns
- **User Behavior** - Session duration, feature usage
- **Authentication** - Login/register success rates
- **Errors** - JavaScript errors, API failures
- **Performance** - Response times, load speeds

### Monitoring URLs
- **Vercel Analytics**: Dashboard → Project → Analytics
- **Google Analytics**: analytics.google.com
- **Custom Events**: Browser console + server logs

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   Database      │
│                 │    │                 │    │                 │
│ • HTML/CSS/JS   │◄──►│ • Flask/Python  │◄──►│ • MongoDB Atlas │
│ • Speech API    │    │ • GROQ AI       │    │ • User Profiles │
│ • Analytics     │    │ • JWT Auth      │    │ • Conversations │
│ • Timers        │    │ • Analytics     │    │ • Analytics     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   External APIs │
                    │                 │
                    │ • GROQ AI       │
                    │ • Weather API   │
                    │ • Analytics     │
                    └─────────────────┘
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Optimus Prime** - Design inspiration
- **GROQ** - AI language model integration  
- **Vercel** - Deployment platform
- **MongoDB** - Database services
- **OpenAI** - Speech synthesis guidance

---

<div align="center">

**Built with ❤️ by [Zaid Shaheed](https://github.com/zaid3004)**

[⭐ Star this repo](https://github.com/zaid3004/Orion-VVA) | [🐛 Report Bug](https://github.com/zaid3004/Orion-VVA/issues) | [💡 Request Feature](https://github.com/zaid3004/Orion-VVA/issues)

</div>