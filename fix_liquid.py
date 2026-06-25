import sys
content = open('templates/profile/dashboard.html', encoding='utf-8').read()

old_css = '''      <!-- Custom Card CSS defined early -->
      <style>
        .card-uiverse {
          position: relative;
          filter: drop-shadow(0 20px 13px rgba(0, 0, 0, 0.03)) drop-shadow(0 8px
 5px rgba(0, 0, 0, 0.08));
          width: 100%;
          height: 9rem;
          overflow: hidden;
          border-radius: 0.75rem;
          background-color: #3d3c3d;
        }
        .card-uiverse-inner {
          position: absolute;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          color: white;
          z-index: 1;
          opacity: 0.9;
          border-radius: 0.7rem;
          top: 1.5px;
          right: 1.5px;
          bottom: 1.5px;
          left: 1.5px;
          background-color: #323132;
        }
        .card-uiverse-blur {
          position: absolute;
          width: 11rem;
          height: 10rem;
          background-color: rgba(255, 255, 255, 0.9);
          filter: blur(40px);
          left: -4rem;
          top: -4rem;
        }
        .card-uiverse .bi {
          font-size: 1.8rem;
          opacity: 0.8;
          margin-bottom: 0.3rem;
        }
        .card-uiverse .stat-label {
          font-size: 0.8rem;
          opacity: 0.9;
          text-transform: uppercase;
          letter-spacing: 1px;
        }
        .card-uiverse .stat-value {
          font-size: 1.7rem;
          font-weight: 800;
          line-height: 1;
        }
      </style>'''

new_css = '''      <!-- Custom Card CSS defined early -->
      <style>
        .morph-wrapper {
          display: flex;
          justify-content: center;
        }
        .morph-card {
          position: relative;
          width: 100%;
          max-width: 180px;
          height: 180px;
          display: flex;
          align-items: center;
          justify-content: center;
          filter: url(#morphGoo);
          cursor: pointer;
        }

        .morph-blob {
          position: absolute;
          background: rgba(255, 255, 255, 0.8);
          backdrop-filter: blur(4px);
          border-radius: 50%;
          transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
          box-shadow: inset 0 0 10px rgba(0,0,0,0.05); /* slightly visible edge */
        }

        .morph-blob-1 {
          width: 140px;
          height: 140px;
          top: 20px;
          left: 20px;
        }

        .morph-blob-2 {
          width: 80px;
          height: 80px;
          top: 0px;
          left: 50px;
        }

        .morph-blob-3 {
          width: 60px;
          height: 60px;
          bottom: 10px;
          left: 60px;
        }

        .morph-card:hover .morph-blob-1 {
          border-radius: 30%;
          width: 130px;
          height: 130px;
          top: 25px;
          left: 25px;
          transform: rotate(-3deg);
          background: #fff;
        }

        .morph-card:hover .morph-blob-2 {
          width: 60px;
          height: 60px;
          top: -5px;
          left: 35px;
          transform: rotate(10deg);
        }

        .morph-card:hover .morph-blob-3 {
          width: 45px;
          height: 45px;
          bottom: 5px;
          left: 100px;
          transform: rotate(-8deg);
        }

        .morph-content {
          position: relative;
          z-index: 2;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
          color: #1C0770;
          transition: all 0.5s ease;
        }

        .morph-icon {
          font-size: 2rem;
          color: rgba(28, 7, 112, 0.6);
          transition: all 0.5s ease;
        }

        .morph-card:hover .morph-icon {
          color: #1C0770;
          transform: translateY(-5px);
          filter: drop-shadow(0 0 8px rgba(28, 7, 112, 0.3));
        }

        .morph-label {
          font-family: inherit;
          font-size: 11px;
          font-weight: 700;
          color: rgba(28, 7, 112, 0.6);
          letter-spacing: 2px;
          text-transform: uppercase;
          transition: all 0.5s ease;
        }

        .morph-card:hover .morph-label {
          color: rgba(28, 7, 112, 0.9);
          letter-spacing: 3px;
        }

        .morph-count {
          font-family: inherit;
          font-size: 32px;
          font-weight: 800;
          color: #1C0770;
          transition: all 0.5s ease;
        }

        .morph-card:hover .morph-count {
          transform: scale(1.1);
          text-shadow: 0 0 15px rgba(28, 7, 112, 0.2);
        }

        .morph-card:active .morph-blob {
          transform: scale(0.92) !important;
          transition-duration: 0.15s;
        }
      </style>'''

old_html = '''      <div class="row g-3 mb-4">
        {% for label, value, icon in dashboard_cards %}
        <div class="col-sm-6 col-xl-3">
          <div class="card-uiverse">
            <div class="card-uiverse-inner">
              <i class="bi {{ icon }}"></i>
              <div class="stat-label">{{ label }}</div>
              <div class="stat-value">{{ value }}</div>
            </div>
            <div class="card-uiverse-blur"></div>
          </div>
        </div>
        {% endfor %}
      </div>'''

new_html = '''      <div class="row g-3 mb-4">
        {% for label, value, icon in dashboard_cards %}
        <div class="col-sm-6 col-xl-3">
          <div class="morph-wrapper">
            <div class="morph-card">
              <div class="morph-blob morph-blob-1"></div>
              <div class="morph-blob morph-blob-2"></div>
              <div class="morph-blob morph-blob-3"></div>
              <div class="morph-content">
                <div class="morph-icon"><i class="bi {{ icon }}"></i></div>
                <div class="morph-label">{{ label }}</div>
                <div class="morph-count">{{ value }}</div>
              </div>
            </div>
          </div>
        </div>
        {% endfor %}
      </div>

      <!-- SVG filter required for goo effect -->
      <svg xmlns="http://www.w3.org/2000/svg" version="1.1" style="display:none;width:0;height:0">
        <defs>
          <filter id="morphGoo">
            <feGaussianBlur in="SourceGraphic" stdDeviation="10" result="blur"></feGaussianBlur>
            <feColorMatrix in="blur" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 20 -9" result="goo"></feColorMatrix>
            <feComposite in="SourceGraphic" in2="goo" operator="atop"></feComposite>
          </filter>
        </defs>
      </svg>'''

# Normalize line endings to avoid mis-match
content = content.replace('\r\n', '\n')
old_css = old_css.replace('\r\n', '\n')
old_html = old_html.replace('\r\n', '\n')

content = content.replace(old_css, new_css)
content = content.replace(old_html, new_html)

with open('templates/profile/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
