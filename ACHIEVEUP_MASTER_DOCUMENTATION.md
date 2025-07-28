# 🎯 ACHIEVEUP INSTRUCTOR PORTAL - MASTER DOCUMENTATION

## 📋 **QUICK REFERENCE**

**Frontend Repository:** https://github.com/nsanchez9009/achieveup-frontend  
**Backend URL:** https://gen-ai-prime-3ddeabb35bd7.herokuapp.com  
**Deployment:** ✅ Live and Operational  
**Status:** ✅ Production Ready

---

## 🚀 **SYSTEM OVERVIEW**

AchieveUp is an AI-powered skill tracking system that transforms traditional assessment into dynamic, skill-based learning experiences. The system enables instructors to:

- **AI-Powered Skill Discovery**: Automatically identify relevant skills for any course
- **Zero-Shot Classification**: Map quiz questions to specific skills using AI
- **Real-Time Analytics**: Monitor student skill development with comprehensive dashboards
- **Evidence-Based Education**: Generate verifiable skill credentials for students

---

## 🏗️ **ARCHITECTURE**

### **Frontend (React TypeScript)**
- **Location**: [nsanchez9009/achieveup-frontend](https://github.com/nsanchez9009/achieveup-frontend)
- **Deployment**: Netlify (achieveup.netlify.app)
- **Technology**: React 18, TypeScript, Tailwind CSS, UCF Branding

### **Backend (Python Quart)**
- **Location**: Current repository
- **Deployment**: Heroku (gen-ai-prime-3ddeabb35bd7.herokuapp.com)
- **Technology**: Quart, MongoDB, OpenAI API, Canvas LMS Integration

---

## 🔗 **API ENDPOINTS SUMMARY**

### **Authentication**
- `POST /auth/login` - Instructor login with role validation
- `POST /auth/signup` - Instructor registration with Canvas token
- `GET /auth/me` - Get current instructor profile
- `POST /auth/validate-canvas-token` - Validate instructor Canvas tokens

### **Canvas Integration**
- `GET /instructor/courses` - Get instructor courses
- `GET /instructor/courses/:id/quizzes` - Get course quizzes
- `GET /instructor/quizzes/:id/questions` - Get quiz questions
- `GET /instructor/students/:courseId` - Get enrolled students

### **AI-Powered Features**
- `POST /instructor/ai/suggest-skills` - AI course skill suggestions
- `POST /instructor/analyze-questions-with-ai` - Question analysis
- `POST /instructor/bulk-assign-skills-with-ai` - Bulk skill assignment

### **Analytics & Dashboard**
- `GET /instructor/dashboard` - Instructor dashboard
- `GET /instructor/courses/:id/analytics` - Course analytics
- `GET /instructor/analytics/risk-assessment/:id` - Risk assessment
- `GET /instructor/analytics/export/:id` - Export analytics

### **Skill Matrix Management**
- `POST /instructor/skill-matrix/create` - Create skill matrix
- `GET /instructor/skill-matrix/:courseId` - Get skill matrix
- `PUT /instructor/skill-matrix/:matrixId` - Update skill matrix

---

## 🤖 **AI INTEGRATION**

### **OpenAI Integration**
```python
# Primary AI with GPT-3.5-turbo
async def generate_ai_skill_suggestions(course_data):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "Expert curriculum designer..."}],
        temperature=0.3
    )
```

### **Fallback System**
```python
COURSE_CODE_MAPPINGS = {
    'COP': ['Programming Fundamentals', 'Algorithm Design'],
    'CDA': ['Computer Architecture', 'System Design'],
    'CNT': ['Network Protocols', 'Network Security'],
    # ... comprehensive mapping
}
```

---

## 🗄️ **DATABASE SCHEMA**

### **Core Collections**
- `AchieveUp_Users` - Instructor accounts with Canvas tokens
- `AchieveUp_Skill_Matrices` - Course skill definitions
- `AchieveUp_Question_Skills` - Question-skill mappings
- `AchieveUp_Progress` - Student progress tracking
- `AchieveUp_Analytics` - Analytics and reporting data

---

## 🔒 **SECURITY FEATURES**

- **JWT Authentication** with instructor role validation
- **Canvas Token Encryption** using Fernet symmetric encryption
- **Role-Based Access Control** with instructor-only endpoints
- **Request Validation** with comprehensive input sanitization
- **CORS Configuration** for frontend integration

---

## 🚀 **DEPLOYMENT & ENVIRONMENT**

### **Environment Variables**
```bash
DATABASE_URL=mongodb+srv://...
JWT_SECRET=your-jwt-secret-key
ENCRYPTION_KEY=your-fernet-encryption-key
OPENAI_API_KEY=your-openai-api-key
CANVAS_API_BASE=https://canvas.instructure.com/api/v1
```

### **Frontend Environment**
```bash
REACT_APP_API_URL=https://gen-ai-prime-3ddeabb35bd7.herokuapp.com
REACT_APP_ENVIRONMENT=production
```

---

## 📊 **ANALYTICS CAPABILITIES**

### **Risk Assessment Algorithm**
Multi-factor analysis including:
- Completion rate (40% weight)
- Average score (30% weight)
- Activity frequency (30% weight)

### **Visualization Types**
- Progress over time (line charts)
- Performance by skill (bar charts)
- Skills mastery overview (radar charts)
- Dashboard overview (combined visualizations)

---

## 🧪 **TESTING STATUS**

✅ **All Endpoints Tested**
- Authentication with valid/invalid credentials
- Canvas integration with real instructor tokens
- AI services with OpenAI API and fallback logic
- Analytics with sample data
- Error handling for all failure scenarios

---

## 📞 **INTEGRATION GUIDE**

### **API Base URL**
```
https://gen-ai-prime-3ddeabb35bd7.herokuapp.com
```

### **Authentication Headers**
```javascript
headers: {
  'Authorization': 'Bearer YOUR_JWT_TOKEN',
  'Content-Type': 'application/json'
}
```

### **Example API Call**
```javascript
// AI Skill Suggestions
POST /instructor/ai/suggest-skills
{
  "courseId": "12345",
  "courseName": "Web Development",
  "courseCode": "COP3530"
}

Response:
{
  "suggestedSkills": [
    {
      "skill": "HTML/CSS Fundamentals",
      "relevance": 0.95,
      "description": "Core web technologies"
    }
  ]
}
```

---

## 🎯 **SUCCESS METRICS**

✅ **All Core Requirements Met:**
1. Instructors can create accounts and validate Canvas tokens
2. AI features provide accurate skill suggestions and analysis
3. Data flows correctly through skill matrices and assignments
4. Analytics provide comprehensive student insights
5. System scales with multiple concurrent users
6. Security is production-ready with encryption
7. Frontend-backend integration is seamless

---

**🎉 ACHIEVEUP IS PRODUCTION-READY AND TRANSFORMING EDUCATION! 🎉** 