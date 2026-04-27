import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import "./Navbar.css";

function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [isLightSection, setIsLightSection] = useState(false);
  const [activeSection, setActiveSection] = useState("#model");

  const scrollToSection = (targetId) => {
    const section = document.querySelector(targetId);

    if (!section) return;

    const sectionTop = section.getBoundingClientRect().top + window.pageYOffset;

    window.scrollTo({
      top: sectionTop,
      behavior: "smooth",
    });
  };

  const handleNavClick = (e, targetId) => {
    e.preventDefault();

    if (location.pathname === "/") {
      scrollToSection(targetId);
    } else {
      navigate("/", { state: { scrollTo: targetId } });
    }
  };

  useEffect(() => {
    if (location.pathname !== "/") return;

    const sections = document.querySelectorAll(".section");

    const handleScroll = () => {
      const checkpoint = window.innerHeight * 0.35;
      let activeLight = false;
      let currentSection = "#model";

      sections.forEach((section) => {
        const rect = section.getBoundingClientRect();

        if (rect.top <= checkpoint && rect.bottom >= checkpoint) {
          activeLight = section.classList.contains("light-section");
          currentSection = `#${section.id}`;
        }
      });

      setIsLightSection(activeLight);
      setActiveSection(currentSection);
    };

    handleScroll();
    window.addEventListener("scroll", handleScroll);

    return () => window.removeEventListener("scroll", handleScroll);
  }, [location.pathname]);

  return (
    <nav className={`navbar-top-right ${isLightSection ? "dark-links" : ""}`}>
      <ul className="navbar-links">
        <li>
          <a
            href="#model"
            className={activeSection === "#model" ? "active" : ""}
            onClick={(e) => handleNavClick(e, "#model")}
          >
            {t("navbar.home")}
          </a>
        </li>

        <li>
          <a
            href="#overview"
            className={activeSection === "#overview" ? "active" : ""}
            onClick={(e) => handleNavClick(e, "#overview")}
          >
            {t("navbar.overview")}
          </a>
        </li>

        <li>
          <a
            href="#home"
            className={activeSection === "#home" ? "active" : ""}
            onClick={(e) => handleNavClick(e, "#home")}
          >
            {t("navbar.get_started")}
          </a>
        </li>

        <li>
          <a
            href="#about"
            className={activeSection === "#about" ? "active" : ""}
            onClick={(e) => handleNavClick(e, "#about")}
          >
            {t("navbar.about_us")}
          </a>
        </li>

        <li>
          <a
            href="#contact"
            className={activeSection === "#contact" ? "active" : ""}
            onClick={(e) => handleNavClick(e, "#contact")}
          >
            {t("navbar.contact")}
          </a>
        </li>
      </ul>
    </nav>
  );
}

export default Navbar;