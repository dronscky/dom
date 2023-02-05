import json
import time
from datetime import datetime

import db


class GetRequestsBot:
    def __init__(self, b_date, session) -> None:
        self._session = session
        self.b_date = b_date
        self.e_date = str(datetime.now().strftime('%d.%m.%Y'))

    def get_json_response(self, page=1):
        json_data = {"statuses":["NOT_SENT"],
                    "sentDatePeriod":{"beginDate":self.b_date,"endDate":self.e_date},
                    "answerUserIds":[],
                    "sortCriteria":{"sortedBy":"LAST_UPDATE_DATE","asceding":'false'}
                    }
        link = f'https://my.dom.gosuslugi.ru/debtreq/api/rest/services/debtreq/sub/search;page={page};itemsPerPage=100'
        while True:
            try:
                r = self._session.post(link, json=json_data)
                break
            except:
                print('Ошибка получения ответа от сервера...')
                time.sleep(5)
        
        match r.status_code:
            case 200:
                try:
                    response_json = r.json()
                    return response_json.get("debtSubReqList")
                except json.JSONDecodeError:
                    print("Ошибка JSONDecodeError")
                    return "JSONDecodeError"
            # case 504:
            #     return "Error 504"
            case _:
                return "Error"

    def manage(self):
        return self.get_json_response()

    def __del__(self) -> None:
        print('Экземпляр класса получения запросов удален...')


class SendResponseBot:
    def __init__(self, session) -> None:
        self._session = session
        # self._db = db.DBClient('Regoper')
        # self._db.create_conn()

    def __del__(self) -> None:
        # self._db.close_conn()
        print('Экземпляр класса ответов удален...')

    def check_for_debt(self, fias_code: str, apartment: str, begin_date: str, end_date: str) -> tuple:
        """   
            Проверка на наличие задолженности в модуле судебной задолженности АРМ  
        """
        if apartment:
            apartment_part = f"supplier_flat_no LIKE '%{apartment}'"
        else:
            apartment_part = f"(supplier_flat_no  = '.' OR supplier_flat_no = '0')"

        sql = f"""
            SELECT last_name, first_name FROM sud_sp sp
            INNER JOIN sud_sp_debtors ssd ON ssd.sp_id = sp.id
            INNER JOIN sud_groups sg ON sg.group_id = sp.group_id
            INNER JOIN occupations o ON o.occ_id_join = sg.occ_id_join
            WHERE supplier_b_fias = '{fias_code}' 
            AND {apartment_part}
            AND sp.date_start between '{begin_date}' AND '{end_date}'
        """
        return self._db.execute_select_command(sql)

    def response_formation(self, deb_id: str, debtor_names=()) -> int:
        """
            Формирование ответа по наличию задолженности
        """
        if debtor_names:
            debtors_list = []
            for debtor in debtor_names:
                first_name, last_name = debtor
                debtors_list.append({"firstName":f"{first_name}","lastName":f"{last_name}","document":None,"attachments":[]})
            
            json_data = {"debtSubReqId":f"{deb_id}","version":0,"debtPresent":True,"additionalInformation":None,
            "debtPersons":debtors_list,"additionalAttachments":[]} 
        else:
            json_data = {"debtSubReqId":f"{deb_id}","version":0,"debtPresent":False}
        link = f"https://my.dom.gosuslugi.ru/debtreq/api/rest/services/debtreq/sub/{deb_id}"
        r = self._session.put(link, json=json_data)
        #   проверка на статус ответа сервера
        # print('статус ответа:', r.status_code)
        return r.status_code

    def send_response(self, deb_id: str, version: int = 1) -> int:
        """
            Подтверждение отправки ответа о задолженности
        """
        json_data = {"debtSubReqId":f"{deb_id}","version":version}        
        link = f"https://my.dom.gosuslugi.ru/debtreq/api/rest/services/debtreq/sub/{deb_id}/send"
        r = self._session.post(link, json=json_data)
        #   проверка на статус ответа сервера
        # print(f"статус подтверждения ответа: {r.status_code}")
        return r.status_code

    def manage(self, deb_id, fias_code, apartment, begin_date, end_date):
        # debtors = self.check_for_debt(fias_code, apartment, begin_date, end_date)
        #   без проверки задолженности из БД
        debtors = []
        if debtors:
            status = "Имеется задолженность"
        else:
            status = "Нет задолженности"
        attempt = 0 #   счетчик попыток восстановления соединения с сервером
        while True:
            if attempt <= 10:
                try:
                    response_formation_status = self.response_formation(deb_id, debtors)
                    if response_formation_status != 403:
                        send_response_status = self.send_response(deb_id)
                        time.sleep(0.5)
                        if send_response_status != 403:
                            attempt = 0
                            return status
                    else:
                        return "Forbidden"
                except:
                    print('Сервер разорвал соединение...')
                    time.sleep(10)
                    attempt += 1
            else:
                break
