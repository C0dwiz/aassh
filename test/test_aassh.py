import sys
import tempfile
from pathlib import Path
from typing import Dict
from unittest.mock import patch

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from aassh import (
    SSHProfile,
    check_mosh_installed,
    create_sample_config,
    error_exit,
    filter_profiles,
    load_config,
    save_config,
)


class TestSSHProfile:
    """Тесты для класса SSHProfile"""

    def test_ssh_profile_creation(self) -> None:
        """Тест создания SSH профиля"""
        profile = SSHProfile(
            name="test-server",
            host="example.com",
            user="user",
            port=22,
            key="~/.ssh/key",
            description="Test server",
            tags=["test", "dev"],
            use_mosh=False,
        )

        assert profile.name == "test-server"
        assert profile.host == "example.com"
        assert profile.user == "user"
        assert profile.port == 22
        assert profile.key == "~/.ssh/key"
        assert profile.description == "Test server"
        assert profile.tags == ["test", "dev"]
        assert profile.use_mosh is False

    def test_connection_string_with_user(self) -> None:
        """Тест формирования строки подключения с пользователем"""
        profile = SSHProfile(name="test", host="host.com", user="user")
        assert profile.connection_string() == "user@host.com"

    def test_connection_string_without_user(self) -> None:
        """Тест формирования строки подключения без пользователя"""
        profile = SSHProfile(name="test", host="host.com")
        assert profile.connection_string() == "host.com"

    def test_to_dict_removes_none_values(self) -> None:
        """Тест конвертации в словарь с удалением None значений"""
        profile = SSHProfile(name="test", host="host.com")
        result = profile.to_dict()

        assert "name" not in result
        assert result["host"] == "host.com"
        assert "user" not in result
        assert "port" not in result

    def test_to_dict_keeps_non_empty_values(self) -> None:
        """Тест сохранения непустых значений в словаре"""
        profile = SSHProfile(
            name="test", host="host.com", user="user", port=22, tags=["test"]
        )
        result = profile.to_dict()

        assert result["host"] == "host.com"
        assert result["user"] == "user"
        assert result["port"] == 22
        assert result["tags"] == ["test"]

    def test_validation_valid_profile(self) -> None:
        """Тест валидации корректного профиля"""
        profile = SSHProfile(name="test", host="valid.com", port=22)
        assert profile.validate() is True

    def test_validation_missing_host(self) -> None:
        """Тест валидации профиля без host"""
        profile = SSHProfile(name="test", host="")
        assert profile.validate() is False

    def test_validation_invalid_port(self) -> None:
        """Тест валидации профиля с некорректным портом"""
        profile = SSHProfile(name="test", host="host.com", port=70000)
        assert profile.validate() is False

    def test_validation_nonexistent_key(self) -> None:
        """Тест валидации профиля с несуществующим ключом"""
        profile = SSHProfile(name="test", host="host.com", key="/nonexistent/path")
        assert profile.validate() is False

    def test_mosh_port_range_validation_valid(self) -> None:
        """Тест валидации корректного диапазона портов Mosh"""
        profile = SSHProfile(
            name="test", host="host.com", use_mosh=True, mosh_port_range="60000:61000"
        )

        assert profile.validate() is True

    def test_mosh_port_range_validation_invalid(self) -> None:
        """Тест валидации некорректного диапазона портов Mosh"""
        profile = SSHProfile(
            name="test", host="host.com", use_mosh=True, mosh_port_range="invalid"
        )

        assert profile.validate() is False


class TestConfigFunctions:
    """Тесты функций работы с конфигурацией"""

    def setup_method(self) -> None:
        """Настройка перед каждым тестом"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / ".aassh" / "config.yml"

        self.home_patcher = patch("aassh.CONFIG_DIR", Path(self.temp_dir) / ".aassh")
        self.home_patcher.start()

        self.file_patcher = patch("aassh.CONFIG_FILE", self.config_path)
        self.file_patcher.start()

    def teardown_method(self) -> None:
        """Очистка после каждого теста"""
        self.home_patcher.stop()
        self.file_patcher.stop()

    def test_save_and_load_config(self) -> None:
        """Тест сохранения и загрузки конфигурации"""
        profiles: Dict[str, SSHProfile] = {
            "server1": SSHProfile(name="server1", host="host1.com", user="user1"),
            "server2": SSHProfile(name="server2", host="host2.com", port=2222),
        }

        save_config(profiles)

        assert self.config_path.exists()

        loaded_profiles = load_config()

        assert "server1" in loaded_profiles
        assert "server2" in loaded_profiles
        assert loaded_profiles["server1"].host == "host1.com"
        assert loaded_profiles["server2"].port == 2222

    def test_load_config_nonexistent_file(self) -> None:
        """Тест загрузки конфигурации из несуществующего файла"""
        profiles = load_config()
        assert profiles == {}

    def test_load_config_invalid_yaml(self) -> None:
        """Тест загрузки конфигурации с некорректным YAML"""
        invalid_yaml = "invalid: yaml: ["
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(invalid_yaml)

        with pytest.raises(SystemExit):
            load_config()

    def test_create_sample_config(self) -> None:
        """Тест создания примерной конфигурации"""

        with patch("aassh.Confirm.ask", return_value=True):
            create_sample_config()

        assert self.config_path.exists()

        content = self.config_path.read_text()
        assert "profiles:" in content
        assert "example:" in content

    def test_create_sample_config_existing_file_cancel(self) -> None:
        """Тест создания конфигурации при существующем файле (отмена)"""

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text("existing config")

        with patch("aassh.Confirm.ask", return_value=False):
            create_sample_config()

        content = self.config_path.read_text()
        assert content == "existing config"


class TestFilterProfiles:
    """Тесты фильтрации профилей"""

    def setup_method(self) -> None:
        """Настройка тестовых данных"""
        self.profiles: Dict[str, SSHProfile] = {
            "web-prod": SSHProfile(
                name="web-prod",
                host="web.prod.com",
                description="Production web server",
                tags=["web", "production"],
            ),
            "db-dev": SSHProfile(
                name="db-dev",
                host="db.dev.com",
                description="Development database",
                tags=["database", "development"],
            ),
            "api-staging": SSHProfile(
                name="api-staging",
                host="api.staging.com",
                description="Staging API server",
                tags=["api", "staging"],
            ),
        }

    def test_filter_by_name(self) -> None:
        """Тест фильтрации по имени"""
        filtered = filter_profiles(self.profiles, "web")
        assert "web-prod" in filtered
        assert "db-dev" not in filtered
        assert "api-staging" not in filtered

    def test_filter_by_description(self) -> None:
        """Тест фильтрации по описанию"""
        filtered = filter_profiles(self.profiles, "database")
        assert "db-dev" in filtered
        assert "web-prod" not in filtered
        assert "api-staging" not in filtered

    def test_filter_by_tag(self) -> None:
        """Тест фильтрации по тегу"""
        filtered = filter_profiles(self.profiles, "production")
        assert "web-prod" in filtered
        assert "db-dev" not in filtered
        assert "api-staging" not in filtered

    def test_filter_case_insensitive(self) -> None:
        """Тест регистронезависимой фильтрации"""
        filtered = filter_profiles(self.profiles, "PRODUCTION")
        assert "web-prod" in filtered

    def test_filter_empty_string(self) -> None:
        """Тест фильтрации с пустой строкой"""
        filtered = filter_profiles(self.profiles, "")
        assert len(filtered) == len(self.profiles)

    def test_filter_no_matches(self) -> None:
        """Тест фильтрации без совпадений"""
        filtered = filter_profiles(self.profiles, "nonexistent")
        assert len(filtered) == 0


class TestUtilityFunctions:
    """Тесты вспомогательных функций"""

    def test_error_exit(self) -> None:
        """Тест функции выхода с ошибкой"""
        with pytest.raises(SystemExit) as exc_info:
            error_exit("Test error", 42)

        assert exc_info.value.code == 42

    def test_check_mosh_installed_true(self) -> None:
        """Тест проверки установки Mosh (установлен)"""
        with patch("aassh.subprocess.run") as mock_subprocess:
            mock_subprocess.return_value.stdout = "mosh 1.3.2"
            mock_subprocess.return_value.returncode = 0

            with patch("aassh.console.print"):
                result = check_mosh_installed()

            assert result is True

    def test_check_mosh_installed_false(self) -> None:
        """Тест проверки установки Mosh (не установлен)"""
        with patch("aassh.subprocess.run") as mock_subprocess:
            mock_subprocess.side_effect = FileNotFoundError()

            with patch("aassh.console.print"):
                result = check_mosh_installed()

            assert result is False


class TestMainFunction:
    """Тесты основной функции"""

    def setup_method(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / ".aassh" / "config.yml"

        self.home_patcher = patch("aassh.CONFIG_DIR", Path(self.temp_dir) / ".aassh")
        self.home_patcher.start()

        self.file_patcher = patch("aassh.CONFIG_FILE", self.config_path)
        self.file_patcher.start()

    def teardown_method(self) -> None:
        self.home_patcher.stop()
        self.file_patcher.stop()

    def test_main_version(self) -> None:
        """Тест вывода версии"""
        with patch("sys.argv", ["aassh", "--version"]):
            with patch("aassh.show_version") as mock_show_version:
                from aassh import main

                main()

        mock_show_version.assert_called_once()

    def test_main_check_mosh(self) -> None:
        """Тест проверки Mosh"""
        with patch("sys.argv", ["aassh", "--check-mosh"]):
            with patch("aassh.check_mosh_installed") as mock_check_mosh:
                from aassh import main

                main()

        mock_check_mosh.assert_called_once()

    def test_main_create_sample_config(self) -> None:
        """Тест создания примерной конфигурации"""
        with patch("sys.argv", ["aassh", "--create-sample-config"]):
            with patch("aassh.create_sample_config") as mock_create_sample:
                from aassh import main

                main()

        mock_create_sample.assert_called_once()

    def test_main_add_profile(self) -> None:
        """Тест добавления профиля"""
        with patch("aassh.load_config") as mock_load_config:
            with patch("aassh.add_profile") as mock_add_profile:
                mock_load_config.return_value = {}
                with patch("sys.argv", ["aassh", "--add"]):
                    from aassh import main

                    main()

            mock_add_profile.assert_called_once()

    def test_main_list_profiles(self) -> None:
        """Тест вывода списка профилей"""
        with patch("aassh.load_config") as mock_load_config:
            with patch("aassh.display_profile_table") as mock_display:
                mock_load_config.return_value = {
                    "test": SSHProfile(name="test", host="host.com")
                }
                with patch("sys.argv", ["aassh", "--list"]):
                    from aassh import main

                    main()

            mock_display.assert_called_once()

    def test_main_interactive_mode(self) -> None:
        """Тест интерактивного режима"""
        with patch("aassh.load_config") as mock_load_config:
            with patch("aassh.interactive_select") as mock_interactive:
                mock_load_config.return_value = {
                    "test": SSHProfile(name="test", host="host.com")
                }
                with patch("sys.argv", ["aassh", "--interactive"]):
                    from aassh import main

                    main()

            mock_interactive.assert_called_once()

    def test_main_connect_to_profile(self) -> None:
        """Тест подключения к конкретному профилю"""
        with patch("aassh.load_config") as mock_load_config:
            with patch("aassh.run_connection") as mock_run_connection:
                test_profile = SSHProfile(name="test", host="host.com")
                mock_load_config.return_value = {"test": test_profile}

                with patch("sys.argv", ["aassh", "test"]):
                    from aassh import main

                    main()

            mock_run_connection.assert_called_once_with(test_profile)

    def test_main_no_config(self) -> None:
        """Тест работы без конфигурации"""
        with patch("aassh.load_config") as mock_load_config:
            mock_load_config.return_value = {}

            # Мокаем console.print чтобы проверить вывод
            with patch("aassh.console.print") as mock_print:
                with patch("sys.argv", ["aassh"]):
                    from aassh import main

                    main()

            assert mock_print.called


class TestIntegration:
    """Интеграционные тесты"""

    def setup_method(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / ".aassh" / "config.yml"

        self.home_patcher = patch("aassh.CONFIG_DIR", Path(self.temp_dir) / ".aassh")
        self.home_patcher.start()

        self.file_patcher = patch("aassh.CONFIG_FILE", self.config_path)
        self.file_patcher.start()

    def teardown_method(self) -> None:
        self.home_patcher.stop()
        self.file_patcher.stop()

    def test_full_config_cycle(self) -> None:
        """Полный цикл работы с конфигурацией"""

        profiles: Dict[str, SSHProfile] = {
            "server1": SSHProfile(
                name="server1",
                host="server1.example.com",
                user="admin",
                port=22,
                description="Primary server",
                tags=["production", "web"],
            ),
            "server2": SSHProfile(
                name="server2",
                host="server2.example.com",
                user="user",
                port=2222,
                use_mosh=True,
                mosh_port_range="60000:61000",
            ),
        }

        save_config(profiles)

        loaded = load_config()

        assert len(loaded) == 2
        assert loaded["server1"].host == "server1.example.com"
        assert loaded["server1"].user == "admin"
        assert loaded["server1"].port == 22
        assert loaded["server2"].use_mosh is True
        assert loaded["server2"].mosh_port_range == "60000:61000"

        filtered = filter_profiles(loaded, "production")
        assert "server1" in filtered
        assert "server2" not in filtered

    def test_yaml_structure(self) -> None:
        """Тест структуры YAML файла"""
        profiles: Dict[str, SSHProfile] = {
            "test-server": SSHProfile(
                name="test-server",
                host="test.com",
                user="testuser",
                port=22,
                tags=["test"],
            )
        }

        save_config(profiles)

        with open(self.config_path, "r") as f:
            config_data = yaml.safe_load(f)

        assert "profiles" in config_data
        assert "test-server" in config_data["profiles"]
        assert config_data["profiles"]["test-server"]["host"] == "test.com"
        assert config_data["profiles"]["test-server"]["user"] == "testuser"
        assert config_data["profiles"]["test-server"]["port"] == 22
        assert config_data["profiles"]["test-server"]["tags"] == ["test"]


@pytest.fixture
def sample_profiles() -> Dict[str, SSHProfile]:
    """Фикстура с примерными профилями"""
    return {
        "web-prod": SSHProfile(
            name="web-prod",
            host="web.prod.com",
            user="admin",
            description="Production web server",
            tags=["web", "production"],
        ),
        "db-dev": SSHProfile(
            name="db-dev",
            host="db.dev.com",
            user="developer",
            description="Development database",
            tags=["db", "development"],
        ),
    }


@pytest.fixture
def temp_config() -> Path:  # type: ignore
    """Фикстура с временной конфигурацией"""
    temp_dir = tempfile.mkdtemp()
    config_path = Path(temp_dir) / ".aassh" / "config.yml"

    home_patcher = patch("aassh.CONFIG_DIR", Path(temp_dir) / ".aassh")
    file_patcher = patch("aassh.CONFIG_FILE", config_path)

    home_patcher.start()
    file_patcher.start()

    yield config_path  # type: ignore

    home_patcher.stop()
    file_patcher.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
