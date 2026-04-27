import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import AOS from "aos";
import "aos/dist/aos.css";
import "./Home.css";
import { FaLinkedin, FaGithub, FaInstagram, FaFacebook } from "react-icons/fa";
import aiImage from "../assets/image2.png";
import { motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { useTranslation } from "react-i18next";

/* Team images */
import supervisorImg from "../assets/hanaaimage.jpeg";
import tawfekImg from "../assets/tawfikimage.jpeg";
import adhamImg from "../assets/adhamimage.jpeg";
import arwaImg from "../assets/arwaimage.jpeg";
import mariamImg from "../assets/maryamimage.jpeg";
import malakImg from "../assets/malakimage.jpeg";
import basmalaImg from "../assets/basmalaimage.jpeg";

const CONTACT_API =
  process.env.REACT_APP_CONTACT_API || "/api/contact";

function HomePage() {
  const { t } = useTranslation();
  const location = useLocation();

  // 🔥 حالة للتحميل
  const [downloadUrl, setDownloadUrl] = useState(null);

  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactMessage, setContactMessage] = useState("");
  const [contactSubmitting, setContactSubmitting] = useState(false);
  const [contactFeedback, setContactFeedback] = useState(null);

  useEffect(() => {
    AOS.init({
      duration: 900,
      once: true,
      offset: 80,
      easing: "ease-in-out",
    });
  }, []);

  useEffect(() => {
    if (location.state && location.state.scrollTo) {
      const section = document.querySelector(location.state.scrollTo);
      if (section) {
        setTimeout(() => {
          section.scrollIntoView({ behavior: "smooth" });
        }, 150);
      }
    }
  }, [location]);

  useEffect(() => {
    const section = document.querySelector("#model");
    if (section) {
      setTimeout(() => {
        section.classList.add("loaded");
      }, 250);
    }
  }, []);

  async function handleContactSubmit(e) {
    e.preventDefault();
    setContactFeedback(null);

    const name = contactName.trim();
    const email = contactEmail.trim();
    const message = contactMessage.trim();

    if (!name || !email || !message) {
      setContactFeedback({ type: "error", key: "error_fill" });
      return;
    }

    setContactSubmitting(true);
    try {
      const res = await fetch(CONTACT_API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, message }),
      });

      const data = await res.json().catch(() => ({}));
      const code = data.message;

      if (res.ok && data.success) {
        setContactFeedback({ type: "success", key: "success" });
        setContactName("");
        setContactEmail("");
        setContactMessage("");
        return;
      }

      const keyMap = {
        fill_fields: "error_fill",
        invalid_email: "error_email",
        payload_too_large: "error_too_long",
        email_not_configured: "error_config",
        send_failed: "error_generic",
      };
      const i18nKey = keyMap[code] || "error_generic";
      setContactFeedback({ type: "error", key: i18nKey });
    } catch {
      setContactFeedback({ type: "error", key: "error_generic" });
    } finally {
      setContactSubmitting(false);
    }
  }

  const members = [
    { img: tawfekImg, name: "Tawfek Mohamed", role: "AI Engineer" },
    { img: adhamImg, name: "Adham Osama", role: "AI Engineer" },
    { img: arwaImg, name: "Arwa Hisham", role: "Frontend Developer" },
    { img: mariamImg, name: "Mariam Salah", role: "Backend Developer" },
    { img: malakImg, name: "Malak Arfa", role: "Flutter Developer" },
    { img: basmalaImg, name: "Basmala Hashim", role: "Flutter Developer" },
  ];

  return (
    <div className="home-container">

      {/* HERO */}
      <section className="section dark-section hero-section loaded" id="model">
        <div className="hero-inner">

          <motion.div
            className="hero-left"
            initial={{ opacity: 0, x: -60 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1.1, ease: "easeOut" }}
          >
            <div className="hero-card">

              <span className="hero-eyebrow" data-aos="fade-down">
                {t("hero.eyebrow")}
              </span>

              <h1 className="hero-title" data-aos="fade-right">
                {t("hero.title")}
              </h1>

              <p className="hero-desc" data-aos="fade-up">
                {t("hero.subtitle")}
              </p>

              <div className="hero-actions" data-aos="zoom-in">
                <button
                  className="hero-btn-primary"
                  onClick={() => {
                    const section = document.getElementById("home");
                    if (section) section.scrollIntoView({ behavior: "smooth" });
                  }}
                >
                  {t("get_started.button")}
                </button>

                <button
                  className="hero-btn-secondary"
                  onClick={() => {
                    const section = document.getElementById("overview");
                    if (section) section.scrollIntoView({ behavior: "smooth" });
                  }}
                >
                  {t("hero.explore_more")}
                </button>
              </div>
            </div>
          </motion.div>

          <motion.div
            className="hero-right"
            initial={{ opacity: 0, x: 60 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1.1, ease: "easeOut" }}
          >
            <div className="hero-brain-glow" />
            <div className="hero-brain-wrap" data-aos="zoom-in">
              <img src={aiImage} alt="AI Brain" className="hero-brain" />
            </div>
          </motion.div>

        </div>

        <motion.div
          animate={{ y: [0, 14, 0] }}
          transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
          className="scroll-btn"
          whileHover={{ scale: 1.08 }}
          onClick={() => {
            const section = document.getElementById("overview");
            if (section) section.scrollIntoView({ behavior: "smooth" });
          }}
        >
          <ChevronDown size={34} color="white" strokeWidth={2.2} />
        </motion.div>
      </section>

     {/* OVERVIEW */}
<section className="section light-section overview-section" id="overview">
  <div className="overview-container" data-aos="fade-up">

    <h2 data-aos="fade-up">{t("overview.title")}</h2>
    <p className="overview-intro" data-aos="fade-up">
      {t("overview.intro")}
    </p>

    <div className="overview-grid">

      <div className="overview-card" data-aos="zoom-in" data-aos-delay="100">
        <h3>{t("overview.goal_title")}</h3>
        <p>{t("overview.goal_text")}</p>
      </div>

      <div className="overview-card" data-aos="zoom-in" data-aos-delay="200">
        <h3>{t("overview.tech_title")}</h3>
        <p>{t("overview.tech_text")}</p>
      </div>

      <div className="overview-card" data-aos="zoom-in" data-aos-delay="300">
        <h3>{t("overview.impact_title")}</h3>
        <p>{t("overview.impact_text")}</p>
      </div>

      <div className="overview-card" data-aos="zoom-in" data-aos-delay="400">
        <h3>{t("overview.features_title")}</h3>
        <p>{t("overview.features_text")}</p>
      </div>

      <div className="overview-card" data-aos="zoom-in" data-aos-delay="500">
        <h3>{t("overview.workflow_title")}</h3>
        <p>{t("overview.workflow_text")}</p>
      </div>

      <div className="overview-card" data-aos="zoom-in" data-aos-delay="600">
        <h3>{t("overview.benefits_title")}</h3>
        <p>{t("overview.benefits_text")}</p>
      </div>

    </div>
  </div>
</section>

      {/* GET STARTED */}
      <section className="section dark-section get-started-section" id="home">
        <div className="upload-wrapper">

          <h2>{t("get_started.title")}</h2>
          <p>{t("get_started.text")}</p>

          <div className="upload-box">

            <input
              type="file"
              id="videoUpload"
              hidden
              onChange={(e) => {
                const file = e.target.files[0];
                if (!file) return;

                const resultContent = "This is the processed result file";

                const blob = new Blob([resultContent], { type: "text/plain" });
                const url = window.URL.createObjectURL(blob);

                setDownloadUrl(url);
              }}
            />

            <label htmlFor="videoUpload" className="upload-btn">
              {t("upload.click_upload")}
            </label>

            <p className="upload-hint">
              {t("upload.description")}
            </p>

            {downloadUrl && (
              <a
                href={downloadUrl}
                download="result.txt"
                className="upload-btn"
                style={{ marginTop: "10px", display: "inline-block" }}
              >
                Download Result
              </a>
            )}

          </div>
        </div>
      </section>

      {/* ABOUT */}
      <section className="section light-section about-section" id="about">
        <div className="team-container" data-aos="fade-up">

          <h2 className="team-title" data-aos="fade-up">{t("about.title")}</h2>
          <p className="team-subtitle" data-aos="fade-up">{t("about.subtitle")}</p>

          <div className="supervisor-block" data-aos="zoom-in">

            <div className="supervisor-avatar-wrap">
              <img
                src={supervisorImg}
                alt="Supervisor"
                className="supervisor-avatar"
              />
            </div>

            <p className="supervisor-label">Supervised by</p>

            <h3 className="supervisor-name">
              Prof. Dr. Hanaa Salem Marie
            </h3>

          </div>

          <div className="team-grid-wrapper">
            <div className="team-grid">

              {members.map((m, i) => (
                <div
                  className="member-circle-card"
                  data-aos="fade-up"
                  data-aos-delay={i * 100}
                  key={i}
                >
                  <img src={m.img} alt={m.name} className="member-circle" />
                  <h3 className="member-name">{m.name}</h3>
                  <p className="member-role">{m.role}</p>
                </div>
              ))}

            </div>
          </div>
        </div>
      </section>

      {/* CONTACT */}
      <section className="section dark-section contact-section" id="contact">

        <div className="contact-wrapper">

          <div className="contact-left" data-aos="fade-right">
            <h2>{t("contact.title")}</h2>
            <p>{t("contact.text")}</p>

            <ul className="social-list">

              <li>
                <a href="https://www.linkedin.com/in/taw7?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app" target="_blank" rel="noreferrer">
                  <FaLinkedin size={28} />
                  <span>{t("contact.socials.linkedin")}</span>
                </a>
              </li>

              <li>
                <a href="https://github.com/TawfekMohamed-7" target="_blank" rel="noreferrer">
                  <FaGithub size={28} />
                  <span>{t("contact.socials.github")}</span>
                </a>
              </li>

              <li>
                <a href="https://www.instagram.com/taww_7?igsh=aHhweXE0Z2Q1eHlp" target="_blank" rel="noreferrer">
                  <FaInstagram size={28} />
                  <span>{t("contact.socials.instagram")}</span>
                </a>
              </li>

              <li>
                <a href="https://www.facebook.com/share/1GbmVJwrdo/" target="_blank" rel="noreferrer">
                  <FaFacebook size={28} />
                  <span>{t("contact.socials.facebook")}</span>
                </a>
              </li>

            </ul>
          </div>
          <div className="contact-right" data-aos="fade-left">

            <h2>{t("contact.send_message")}</h2>

            <form className="contact-form" onSubmit={handleContactSubmit}>
              <input
                type="text"
                placeholder={t("contact.name_placeholder")}
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
                required
              />
              <input
                type="email"
                placeholder={t("contact.email_placeholder")}
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
                required
              />
              <textarea
                placeholder={t("contact.message_placeholder")}
                rows="5"
                value={contactMessage}
                onChange={(e) => setContactMessage(e.target.value)}
                required
              />

              <button type="submit" className="contact-btn" disabled={contactSubmitting}>
                {contactSubmitting ? t("contact.sending") : t("contact.submit_button")}
              </button>

              {contactFeedback && (
                <p
                  style={{
                    marginTop: "10px",
                    color: contactFeedback.type === "success" ? "#22c55e" : "#ef4444",
                  }}
                >
                  {t(`contact.${contactFeedback.key}`)}
                </p>
              )}
            </form>

          </div>

        </div>

      </section>

    </div>
  );
}

export default HomePage;