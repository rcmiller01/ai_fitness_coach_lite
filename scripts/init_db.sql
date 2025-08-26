-- Database Initialization Script for AI Fitness Coach
-- Creates tables, indexes, and initial data

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    profile_data JSONB DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    subscription_type VARCHAR(50) DEFAULT 'free',
    subscription_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE
);

-- Create workouts table
CREATE TABLE IF NOT EXISTS workouts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    workout_id VARCHAR(255) UNIQUE NOT NULL,
    workout_type VARCHAR(100),
    title VARCHAR(255),
    description TEXT,
    exercises JSONB DEFAULT '[]',
    metrics JSONB DEFAULT '{}',
    duration INTEGER, -- in seconds
    calories_burned INTEGER,
    difficulty_level VARCHAR(20),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Create plugin_licenses table
CREATE TABLE IF NOT EXISTS plugin_licenses (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    plugin_id VARCHAR(255) NOT NULL,
    license_key VARCHAR(255) NOT NULL,
    license_type VARCHAR(50) DEFAULT 'trial', -- trial, personal, professional
    activation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expiry_date TIMESTAMP,
    trial_used BOOLEAN DEFAULT FALSE,
    activation_count INTEGER DEFAULT 1,
    max_activations INTEGER DEFAULT 3,
    device_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, plugin_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Create user_analytics table
CREATE TABLE IF NOT EXISTS user_analytics (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB DEFAULT '{}',
    plugin_id VARCHAR(255),
    session_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Create exercise_library table
CREATE TABLE IF NOT EXISTS exercise_library (
    id SERIAL PRIMARY KEY,
    exercise_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    muscle_groups TEXT[],
    equipment TEXT[],
    difficulty_level VARCHAR(20),
    instructions TEXT[],
    description TEXT,
    video_url VARCHAR(500),
    image_url VARCHAR(500),
    plugin_id VARCHAR(255),
    is_premium BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create user_progress table
CREATE TABLE IF NOT EXISTS user_progress (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    metric_type VARCHAR(100) NOT NULL, -- weight, body_fat, muscle_mass, etc.
    metric_value DECIMAL(10,2),
    unit VARCHAR(20),
    recorded_date DATE DEFAULT CURRENT_DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Create plugin_downloads table
CREATE TABLE IF NOT EXISTS plugin_downloads (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    plugin_id VARCHAR(255) NOT NULL,
    version VARCHAR(50),
    download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    download_size BIGINT,
    installation_status VARCHAR(50) DEFAULT 'pending',
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Create payment_transactions table
CREATE TABLE IF NOT EXISTS payment_transactions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    transaction_id VARCHAR(255) UNIQUE NOT NULL,
    plugin_id VARCHAR(255),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    payment_method VARCHAR(50),
    payment_status VARCHAR(50) DEFAULT 'pending',
    stripe_payment_intent_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Create notification_logs table
CREATE TABLE IF NOT EXISTS notification_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    notification_type VARCHAR(100) NOT NULL,
    title VARCHAR(255),
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

CREATE INDEX IF NOT EXISTS idx_workouts_user_id ON workouts(user_id);
CREATE INDEX IF NOT EXISTS idx_workouts_workout_type ON workouts(workout_type);
CREATE INDEX IF NOT EXISTS idx_workouts_created_at ON workouts(created_at);
CREATE INDEX IF NOT EXISTS idx_workouts_completed_at ON workouts(completed_at);

CREATE INDEX IF NOT EXISTS idx_plugin_licenses_user_id ON plugin_licenses(user_id);
CREATE INDEX IF NOT EXISTS idx_plugin_licenses_plugin_id ON plugin_licenses(plugin_id);
CREATE INDEX IF NOT EXISTS idx_plugin_licenses_expiry_date ON plugin_licenses(expiry_date);

CREATE INDEX IF NOT EXISTS idx_user_analytics_user_id ON user_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_user_analytics_event_type ON user_analytics(event_type);
CREATE INDEX IF NOT EXISTS idx_user_analytics_timestamp ON user_analytics(timestamp);
CREATE INDEX IF NOT EXISTS idx_user_analytics_plugin_id ON user_analytics(plugin_id);

CREATE INDEX IF NOT EXISTS idx_exercise_library_category ON exercise_library(category);
CREATE INDEX IF NOT EXISTS idx_exercise_library_plugin_id ON exercise_library(plugin_id);
CREATE INDEX IF NOT EXISTS idx_exercise_library_name_trgm ON exercise_library USING gin(name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_user_progress_user_id ON user_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_metric_type ON user_progress(metric_type);
CREATE INDEX IF NOT EXISTS idx_user_progress_recorded_date ON user_progress(recorded_date);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_user_id ON payment_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_status ON payment_transactions(payment_status);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_created_at ON payment_transactions(created_at);

-- Create functions for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workouts_updated_at BEFORE UPDATE ON workouts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_plugin_licenses_updated_at BEFORE UPDATE ON plugin_licenses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_exercise_library_updated_at BEFORE UPDATE ON exercise_library
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payment_transactions_updated_at BEFORE UPDATE ON payment_transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial exercise library data
INSERT INTO exercise_library (exercise_id, name, category, muscle_groups, equipment, difficulty_level, instructions, description) VALUES
('push_up', 'Push-up', 'bodyweight', ARRAY['chest', 'triceps', 'shoulders'], ARRAY[], 'beginner', 
 ARRAY['Start in plank position', 'Lower body to ground', 'Push back up to start'], 
 'Classic bodyweight exercise for upper body strength'),
 
('squat', 'Bodyweight Squat', 'bodyweight', ARRAY['quadriceps', 'glutes', 'hamstrings'], ARRAY[], 'beginner',
 ARRAY['Stand with feet shoulder-width apart', 'Lower down as if sitting in chair', 'Return to standing'],
 'Fundamental lower body exercise'),
 
('plank', 'Plank', 'core', ARRAY['core', 'shoulders'], ARRAY[], 'beginner',
 ARRAY['Start in push-up position on forearms', 'Keep body straight', 'Hold position'],
 'Core stability exercise'),
 
('burpee', 'Burpee', 'full_body', ARRAY['full_body'], ARRAY[], 'intermediate',
 ARRAY['Start standing', 'Drop to squat thrust', 'Jump back up with arms overhead'],
 'High-intensity full-body exercise'),
 
('mountain_climber', 'Mountain Climbers', 'cardio', ARRAY['core', 'shoulders', 'legs'], ARRAY[], 'intermediate',
 ARRAY['Start in plank position', 'Alternate bringing knees to chest', 'Keep core engaged'],
 'Dynamic cardio and core exercise')

ON CONFLICT (exercise_id) DO NOTHING;

-- Insert initial user roles and permissions
CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    permissions JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO user_roles (role_name, permissions) VALUES
('free_user', '{"plugins": ["basic"], "workouts": 5, "analytics": "basic"}'),
('premium_user', '{"plugins": ["all"], "workouts": "unlimited", "analytics": "advanced"}'),
('admin', '{"plugins": ["all"], "workouts": "unlimited", "analytics": "full", "manage_users": true}')
ON CONFLICT (role_name) DO NOTHING;

-- Create view for user statistics
CREATE OR REPLACE VIEW user_workout_stats AS
SELECT 
    u.user_id,
    u.username,
    COUNT(w.id) as total_workouts,
    COALESCE(SUM(w.duration), 0) as total_duration_seconds,
    COALESCE(SUM(w.calories_burned), 0) as total_calories,
    MAX(w.completed_at) as last_workout_date,
    DATE_TRUNC('week', CURRENT_DATE) - DATE_TRUNC('week', MIN(w.created_at)) as weeks_active
FROM users u
LEFT JOIN workouts w ON u.user_id = w.user_id AND w.completed_at IS NOT NULL
GROUP BY u.user_id, u.username;

-- Create view for plugin usage analytics
CREATE OR REPLACE VIEW plugin_usage_stats AS
SELECT 
    plugin_id,
    COUNT(DISTINCT user_id) as active_users,
    COUNT(*) as total_events,
    DATE_TRUNC('day', timestamp) as date
FROM user_analytics 
WHERE plugin_id IS NOT NULL
GROUP BY plugin_id, DATE_TRUNC('day', timestamp)
ORDER BY date DESC;

COMMENT ON DATABASE fitness_coach IS 'AI Fitness Coach Production Database';
COMMENT ON TABLE users IS 'User accounts and profile information';
COMMENT ON TABLE workouts IS 'User workout sessions and exercise data';
COMMENT ON TABLE plugin_licenses IS 'Plugin licensing and activation records';
COMMENT ON TABLE user_analytics IS 'User behavior and interaction analytics';
COMMENT ON TABLE exercise_library IS 'Exercise database with instructions and metadata';

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO fitness_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO fitness_user;