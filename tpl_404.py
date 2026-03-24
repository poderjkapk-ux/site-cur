# tpl_404.py

HTML_404_TEMPLATE = """
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Сторінку не знайдено - {site_title}</title>
    
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family={font_family_serif_encoded}:wght@400;600;700&family={font_family_sans_encoded}:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
      :root {{
        /* --- Dynamic Variables --- */
        --primary: {primary_color_val};
        --secondary: {secondary_color_val};
        --bg-color: {background_color_val};
        --text-main: {text_color_val};
        --footer-bg: {footer_bg_color_val};
        --footer-text: {footer_text_color_val};
        --nav-bg: {category_nav_bg_color};
        --nav-text: {category_nav_text_color};
        --header-img: url('/{header_image_url}');
        
        /* --- System Colors & Shadows --- */
        --surface: #ffffff;
        --surface-glass: rgba(255, 255, 255, 0.95);
        --border-light: rgba(0, 0, 0, 0.08);
        
        --shadow-sm: 0 4px 12px rgba(0,0,0,0.05);
        --shadow-md: 0 12px 30px rgba(0,0,0,0.08);
        --shadow-lg: 0 20px 60px rgba(0,0,0,0.15);
        
        /* --- Animation --- */
        --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
        
        /* --- Fonts --- */
        --font-sans: '{font_family_sans_val}', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        --font-serif: '{font_family_serif_val}', serif;
      }}
      
      html {{ scroll-behavior: smooth; -webkit-text-size-adjust: 100%; }}
      * {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; outline: none; }}
      
      body {{
        margin: 0;
        background-color: var(--bg-color);
        background-image: 
            radial-gradient(at 0% 0%, color-mix(in srgb, var(--primary), transparent 97%), transparent 60%),
            radial-gradient(at 100% 100%, color-mix(in srgb, var(--secondary), transparent 97%), transparent 60%);
        background-attachment: fixed;
        color: var(--text-main);
        font-family: var(--font-sans);
        display: flex; flex-direction: column; min-height: 100vh;
        -webkit-font-smoothing: antialiased;
        font-size: 15px;
        line-height: 1.5;
      }}

      h1, h2, h3, h4, .serif {{ font-family: var(--font-serif); margin: 0; color: var(--text-main); }}
      a {{ text-decoration: none; color: inherit; }}

      /* --- HEADER --- */
      header {{
          position: relative;
          height: 35vh; min-height: 250px;
          display: flex; flex-direction: column; align-items: center; justify-content: center;
          text-align: center; color: white;
          border-radius: 0 0 50px 50px;
          overflow: hidden;
          box-shadow: 0 10px 50px rgba(0,0,0,0.15);
          margin-bottom: 20px;
      }}
      .header-bg {{
          position: absolute; inset: 0;
          background-image: var(--header-img);
          background-size: cover; background-position: center;
          z-index: 0;
      }}
      header::after {{
          content: ''; position: absolute; inset: 0;
          background: linear-gradient(to bottom, rgba(0,0,0,0.3), rgba(0,0,0,0.7));
          z-index: 1;
          backdrop-filter: blur(2px);
      }}
      
      .header-content {{ position: relative; z-index: 2; width: 90%; max-width: 800px; animation: fadeUp 1s var(--ease-out); }}
      .header-logo {{ 
          height: 80px; width: auto; margin-bottom: 15px; 
          filter: drop-shadow(0 10px 25px rgba(0,0,0,0.3));
      }}
      header h1 {{ 
          font-size: clamp(2rem, 5vw, 3.5rem); font-weight: 700; 
          text-shadow: 0 4px 25px rgba(0,0,0,0.4);
          color: white;
      }}

      /* --- 404 CONTENT --- */
      .container {{ max-width: 1280px; margin: 0 auto; padding: 0 25px; flex-grow: 1; display: flex; align-items: center; justify-content: center; }}
      
      .error-wrapper {{
          text-align: center;
          padding: 60px 20px;
          animation: fadeUp 0.8s var(--ease-out);
          background: rgba(255, 255, 255, 0.5);
          backdrop-filter: blur(20px);
          border-radius: 30px;
          border: 1px solid rgba(255, 255, 255, 0.5);
          box-shadow: var(--shadow-lg);
          max-width: 600px;
          width: 100%;
      }}

      .error-code {{
          font-family: var(--font-serif);
          font-size: 8rem;
          line-height: 1;
          color: var(--primary);
          opacity: 0.8;
          margin-bottom: 0;
      }}
      
      .error-icon {{
          font-size: 4rem;
          color: var(--text-main);
          margin-bottom: 20px;
          animation: float 3s ease-in-out infinite;
          display: inline-block;
      }}

      .error-title {{
          font-size: 2rem;
          margin: 10px 0 20px;
          font-weight: 700;
      }}
      
      .error-text {{
          font-size: 1.1rem;
          color: #64748b;
          margin-bottom: 40px;
          line-height: 1.6;
      }}

      .main-btn {{ 
          display: inline-flex; align-items: center; gap: 10px;
          padding: 16px 32px;
          background: var(--primary); color: white; 
          border: none; border-radius: 16px; 
          font-size: 1.1rem; font-weight: 600; 
          cursor: pointer; transition: all 0.2s;
          box-shadow: 0 8px 20px color-mix(in srgb, var(--primary), transparent 60%);
          text-decoration: none;
      }}
      .main-btn:hover {{ background: color-mix(in srgb, var(--primary), black 10%); transform: translateY(-3px); }}
      
      /* --- FOOTER --- */
      footer {{ 
          background: var(--footer-bg); color: var(--footer-text); 
          padding: 60px 20px 30px; margin-top: 40px; 
      }}
      .footer-content {{ 
          display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
          gap: 40px; max-width: 1200px; margin: 0 auto; 
      }}
      .footer-section h4 {{ 
          font-size: 0.9rem; margin-bottom: 20px; opacity: 0.7; 
          text-transform: uppercase; font-weight: 800; letter-spacing: 1.5px;
          color: var(--footer-text);
      }}
      .footer-link {{ 
          display: flex; align-items: center; gap: 12px; margin-bottom: 14px; 
          color: inherit; text-decoration: none; opacity: 0.8; transition: opacity 0.2s; font-size: 1rem;
      }}
      .footer-link:hover {{ opacity: 1; }}
      .footer-link i {{ width: 20px; text-align: center; }}
      
      .social-links {{ display: flex; gap: 15px; }}
      .social-links a {{ 
          display: flex; width: 40px; height: 40px; border-radius: 12px; 
          background: rgba(255,255,255,0.15); align-items: center; justify-content: center; 
          color: white; text-decoration: none; transition: all 0.3s;
          font-size: 1.2rem;
      }}
      .social-links a:hover {{ background: var(--primary); transform: translateY(-3px); }}

      @keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
      @keyframes float {{ 0% {{ transform: translateY(0px) rotate(0deg); }} 50% {{ transform: translateY(-10px) rotate(5deg); }} 100% {{ transform: translateY(0px) rotate(0deg); }} }}
      
      @media (max-width: 768px) {{
          header {{ height: 25vh; border-radius: 0 0 30px 30px; }}
          header h1 {{ font-size: 2rem; }}
          .error-code {{ font-size: 6rem; }}
          .error-wrapper {{ padding: 40px 20px; }}
      }}
    </style>
</head>
<body>
    <header>
        <div class="header-bg"></div>
        <div class="header-content">
            <div class="header-logo-container">{logo_html}</div>
            <h1>{site_header_text}</h1>
        </div>
    </header>
    
    <div class="container">
        <div class="error-wrapper">
            <div class="error-icon">
                <i class="fa-solid fa-pizza-slice"></i>
            </div>
            <h1 class="error-code">404</h1>
            <h2 class="error-title">Ой! Сторінку не знайдено</h2>
            <p class="error-text">
                Схоже, що сторінка, яку ви шукаєте, була переміщена або видалена. 
                Але не хвилюйтеся, наше меню все ще на місці!
            </p>
            <a href="/" class="main-btn">
                <i class="fa-solid fa-house"></i> Повернутися до меню
            </a>
        </div>
    </div>

    <footer>
        <div class="footer-content">
            <div class="footer-section">
                <h4>Контакти</h4>
                <div class="footer-link"><i class="fa-solid fa-location-dot"></i> <span>{footer_address}</span></div>
                <a href="tel:{footer_phone}" class="footer-link"><i class="fa-solid fa-phone"></i> <span>{footer_phone}</span></a>
                <div class="footer-link"><i class="fa-regular fa-clock"></i> <span>{working_hours}</span></div>
            </div>
            <div class="footer-section">
                <h4>Інформація</h4>
                <div class="menu-pages-links">
                    {menu_links_html}
                </div>
            </div>
            <div class="footer-section">
                <h4>Ми в соцмережах</h4>
                <div class="social-links">{social_links_html}</div>
            </div>
        </div>
        <div style="text-align:center; margin-top:40px; opacity:0.4; font-size:0.85rem;">
            © 2026 {site_title}. All rights reserved.
        </div>
    </footer>
</body>
</html>
"""