import os
import textwrap

path_tsx = r'C:\Users\DATA FORCE\OneDrive\Pictures\Screenshots\Desktop\pythin\epu_public_home\src\pages\PresidentSpeech.tsx'
path_app = r'C:\Users\DATA FORCE\OneDrive\Pictures\Screenshots\Desktop\pythin\epu_public_home\src\App.tsx'

content = """import React from 'react';
import { motion } from 'framer-motion';
import { Target, Lightbulb, Users, Globe, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function PresidentSpeech() {
  const fadeUp = {
    hidden: { opacity: 0, y: 30 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: "easeOut" } }
  };

  const staggerContainer = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.15 }
    }
  };

  return (
    <div className="bg-[#f8f9fa] min-h-screen font-sans overflow-x-hidden">
      {/* 1. Hero Section */}
      <section className="relative bg-[#1a0f4a] pt-24 pb-32 px-6 overflow-hidden">
        {/* Background elements */}
        <div className="absolute inset-0 opacity-20 bg-[url('https://images.unsplash.com/photo-1523240795612-9a054b0db644?ixlib=rb-4.0.3&auto=format&fit=crop&w=2000&q=80')] bg-cover bg-center mix-blend-overlay"></div>
        <div className="absolute -top-[20%] -right-[10%] w-[600px] h-[600px] rounded-full border border-white/10 pointer-events-none"></div>
        <div className="absolute top-[10%] -left-[10%] w-[400px] h-[400px] rounded-full border border-white/10 pointer-events-none"></div>
        
        <div className="relative max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-12 z-10">
          <motion.div 
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
            className="md:w-3/5 text-left"
          >
            <span className="text-[#ffb700] text-sm font-bold tracking-[0.2em] uppercase mb-4 block">Leadership Vision</span>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-serif text-white mb-6 leading-tight">
              A Message from the President
            </h1>
            <p className="text-blue-100/90 text-lg md:text-xl font-light leading-relaxed max-w-xl">
              "We strive to provide the opportunity for every student to make a positive impact on our world."
            </p>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1, delay: 0.2 }}
            className="md:w-2/5 flex justify-center md:justify-end"
          >
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-tr from-[#ffb700] to-[#1a0f4a] rounded-2xl transform rotate-3 scale-105 opacity-50 blur-lg"></div>
              <img 
                src="https://images.unsplash.com/photo-1560250097-0b93528c311a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80" 
                alt="University President" 
                className="relative z-10 w-64 md:w-80 h-auto rounded-2xl shadow-2xl border-4 border-white/10 object-cover aspect-[3/4]"
              />
            </div>
          </motion.div>
        </div>
      </section>

      {/* 2. Main Content & Core Values Split Grid */}
      <section className="max-w-7xl mx-auto px-4 md:px-8 py-16 md:py-24 -mt-20 relative z-20">
        <div className="grid lg:grid-cols-12 gap-12 items-start">
          
          {/* Presidential Speech Content (Left, 8 cols) */}
          <motion.div 
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={fadeUp}
            className="lg:col-span-8 bg-white rounded-[2rem] p-8 md:p-12 lg:p-16 shadow-xl border border-gray-100 text-gray-600 text-lg/8 font-light"
          >
            <h2 className="text-3xl font-bold text-[#1a0f4a] mb-8 font-serif">Welcome to Erbil Polytechnic University!</h2>
            
            <p className="mb-6">
              Thank you for your presence and for allowing me to address you today, academic staff, faculty, students, stakeholders and partners.
            </p>
            
            <p className="mb-6">
              After my selection to lead the Erbil Polytechnic University in April 2022, I immediately began to try to understand the environment of our university. Accordingly, I resolved to develop EPU into a university dedicated to meeting the needs of our community by providing students and faculty the best quality of classroom education, professional development and technical excellence in preparation for service in our fast-paced, technologically-advanced world. 
            </p>

            <blockquote className="my-10 pl-6 border-l-4 border-[#ffb700] text-xl md:text-2xl text-[#1a0f4a] font-serif italic leading-relaxed">
              At EPU, we place great emphasis on practical learning; learning which is appropriate for meeting the needs of our community.
            </blockquote>
            
            <p className="mb-6">
              We provide high–quality technical educational experiences in a safe environment for all our students and faculty members. To this end, one of our top priorities is to enable students to translate classroom theory and concepts into practical application.
            </p>

            <p className="mb-6">
              We make every effort to enhance the EPU environment, so that every person feels proud and valued of educational endeavors and their academic achievements. I believe the success of our university hinges upon our faculty members, students and academic staff growing and thriving as they pursue their personal academic goals, supported by our kind and generous partners and stakeholders.
            </p>

            <p className="mb-6">
              Currently, at EPU, we are a booming, welcoming community of learning, which attracts thousands of national and international students, instructors, innovators and academic leaders.
            </p>
            
            <p className="mb-6">
              I am convinced, that together, we can increase our research results and drive positive social, economic, cultural, and environmental change. I am determined to deepen our commitment to our university missions. I will foster an active and engaged learning environment. Also, I am striving to cultivate a sense of belonging among staff through creating many opportunities to collaborate, and expand our national and international academic relations with our partners through joint research, training and exchanging of students, as well as faculty members.
            </p>

            <p className="mb-6 font-medium text-gray-800">
              I will embrace every opportunity that lay ahead as I believe that higher education institutions are the only means by which we can drive positive change in the community.
            </p>

            <div className="mt-12 pt-8 border-t border-gray-100 flex items-center justify-between">
              <div>
                <img src="/epu-logo.png" alt="EPU" className="w-16 opacity-50 grayscale mb-2" />
                <p className="text-sm font-bold text-[#1a0f4a] uppercase tracking-widest">Office of the President</p>
                <p className="text-xs text-gray-400 mt-1">Erbil Polytechnic University</p>
              </div>
            </div>
          </motion.div>

          {/* Interactive Vision Focus Cards (Right, 4 cols) */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            <motion.div 
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={staggerContainer}
              className="sticky top-24"
            >
              <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6 lg:mt-8 px-2">Strategic Pillars</h3>
              
              {[
                { icon: <Target size={24} />, title: "21st Century Skills", desc: "Educating and equipping Gen Z students with skills for effective cross-cultural communication and creative thinking." },
                { icon: <Lightbulb size={24} />, title: "Labor Market Focus", desc: "Creative, comprehensive, inclusive technical education based on dynamic regional needs." },
                { icon: <Users size={24} />, title: "Teamwork & Care", desc: "Developing hyper-critical thinking and teamwork skills demanded by modern employers." },
                { icon: <Globe size={24} />, title: "Global & Local Impact", desc: "Partnerships across education, health care, business, and NGOs for a prosperous future." }
              ].map((pillar, i) => (
                <motion.div 
                  key={i}
                  variants={fadeUp}
                  className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 hover:shadow-xl hover:border-[#1a0f4a]/20 transition-all duration-300 group mb-4"
                >
                  <div className="flex items-start gap-4">
                    <div className="p-3 bg-[#f8f9fc] text-[#1a0f4a] rounded-xl group-hover:bg-[#1a0f4a] group-hover:text-white transition-colors duration-300 shrink-0">
                      {pillar.icon}
                    </div>
                    <div>
                      <h4 className="font-bold text-gray-900 mb-1 leading-tight group-hover:text-[#1a0f4a] transition-colors">{pillar.title}</h4>
                      <p className="text-sm text-gray-500 leading-relaxed">{pillar.desc}</p>
                    </div>
                  </div>
                </motion.div>
              ))}

              <motion.div variants={fadeUp} className="mt-8">
                <div className="bg-[#1a0f4a] text-white p-8 rounded-2xl relative overflow-hidden group">
                  <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-white via-transparent to-transparent"></div>
                  <div className="relative z-10 text-center">
                    <h4 className="text-2xl font-serif mb-2">11,000+</h4>
                    <p className="text-sm text-blue-200 mb-4">Students crafting their future</p>
                    <div className="flex items-center justify-center gap-4 text-xs font-bold tracking-wider text-white/50 uppercase">
                      <span>6 Colleges</span>
                      <span className="w-1.5 h-1.5 rounded-full bg-[#ffb700]"></span>
                      <span>6 Institutes</span>
                    </div>
                  </div>
                </div>
              </motion.div>

            </motion.div>
          </div>

        </div>
      </section>

      {/* 3. Bottom CTA */}
      <section className="bg-white py-24 text-center border-t border-gray-100">
        <motion.div 
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeUp}
          className="max-w-3xl mx-auto px-6"
        >
          <h2 className="text-3xl md:text-4xl font-serif text-[#1a0f4a] mb-6">Join our thriving community</h2>
          <p className="text-gray-500 text-lg mb-10">Discover your path at Erbil Polytechnic University and make an impact on the world.</p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/academics" className="px-8 py-4 bg-[#1a0f4a] text-white rounded-xl font-bold tracking-wide hover:bg-[#2c1c7a] hover:shadow-lg transition-all flex items-center justify-center gap-2 group w-full sm:w-auto">
              Explore Programs <ArrowRight className="size-4 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link to="/about" className="px-8 py-4 bg-gray-50 text-gray-700 rounded-xl font-bold tracking-wide hover:bg-gray-100 transition-all text-center w-full sm:w-auto">
              Read Our Story
            </Link>
          </div>
        </motion.div>
      </section>

    </div>
  );
}
"""

with open(path_tsx, 'w', encoding='utf-8') as f:
    f.write(content)

# Now, we need to inject the route into App.tsx to make the page accessible.
with open(path_app, 'r', encoding='utf-8') as f:
    app_text = f.read()

# Add import
if 'import PresidentSpeech from' not in app_text:
    # Insert right after import About from './pages/About';
    import_target = "import History from './pages/History';"
    app_text = app_text.replace(import_target, f"{import_target}\nimport PresidentSpeech from './pages/PresidentSpeech';")

# Add route mapping
if '<Route path="/president-message"' not in app_text:
    route_target = '<Route path="/history" element={<History />} />'
    app_text = app_text.replace(route_target, f"{route_target}\n          <Route path=\"/president-message\" element={{<PresidentSpeech />}} />")

with open(path_app, 'w', encoding='utf-8') as f:
    f.write(app_text)

print("Created PresidentSpeech.tsx and updated App.tsx routing.")
