
import sys
import os

from src.NewTun.DongliFanzhuan import DongliFanzhuan
from src.NewTun.TDX.Core import Core

curPath=os.path.abspath(os.path.dirname(__file__))
rootPath=os.path.split(curPath)[0]
sys.path.append(rootPath)
sys.path.append("path")
print(sys.path)

import time
import os
import uuid
import pymysql
import threadpool

from PIL import Image, ImageDraw, ImageFont

from src.NewTun.ApplicationWithDraw import ApplicationWithDraw
from src.NewTun.Connection import Connection
from src.NewTun.QueryStock import QueryStock
from src.NewTun.ScanFlag import ScanFlag
from src.NewTun.SendEmail import SendEmail
from src.NewTun.Statistics import Statistics
from src.NewTun.StockInfoSyn import StockInfoSyn
from src.NewTun.Application import Application


class zMain:

    #是否显示出来
    isShow=True
    candidate=[]
    currentPath=''
    connection = None

    #初始化函数
    def __init__(self):
        self.currentPath=os.getcwd()
        self.connection = Connection()
        if self.connection.savePath!='':
            self.currentPath=self.connection.savePath
            if not os.path.exists(self.currentPath+"\\temp\\"):
                os.makedirs(self.currentPath)
        #设置一个默认的图片
        if not os.path.exists(self.currentPath+"\\temp\\zMain.png"):
            imgHeight=100
            imgWidth=500
            letterHeight=10
            letterWidth=50
            imgSize = (imgWidth, imgHeight)
            bg_color = (255, 255, 255)
            img = Image.new("RGB", imgSize, bg_color)
            drawBrush = ImageDraw.Draw(img)
            textY0 = (imgHeight - letterHeight + 1) / 2
            textY0 = int(textY0)
            textX0 = int((imgWidth - letterWidth + 1) / 2)
            print('text location:', (textX0, textY0))
            print('text size (width,height):', letterWidth, letterHeight)
            print('img size(width,height):', imgSize)
            font = ImageFont.truetype("C:\\Windows\\Fonts\\Arial.ttf", size=20)
            fg_color = (0, 0, 0)
            drawBrush.text((textX0, textY0), "---zMain---", fill=fg_color, font=font)
            img.save(self.currentPath+"\\temp\\zMain.png",quality=60)

    #通过股票数据
    def synHistoryStock(self):
        if self.connection.syn=='True':
            # 通达信自动下载
            if self.connection.tdxDayPath != '' and os.path.exists(self.connection.tdxDayPath):
                core = Core()
                core.exec()
            print("-----------------------------syn stock------------------------------------")
            print("start time:"+time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
            syn=StockInfoSyn()
            syn.isJgdy=self.connection.isJgdy
            syn.synStockInfo()
            print("start time:"+time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))





    def doScan(self,t,stockLength,basicStock,today,cursor,connect):
        allStocklength=stockLength
        scanFlag=ScanFlag()
        for i in range(allStocklength):
            item=basicStock[i]
            if item[1].__contains__("ST"):
                continue
            baseIndex=int(scanFlag.readIndex(t,today))
            if baseIndex<=i:
                scanFlag.writeIndex(t,today,i)
            elif baseIndex>i:
                print("thread"+str(t)+"\t"+item[1]+"\t已扫描...")
                continue
            if baseIndex==allStocklength-1:
                scanFlag.writeIndex(t,today,0)

            test = Application()
            if item[0]!=None and item[1]!=None and item[2]!=None and item[3]!=None :
                print("thread-"+str(t)+"\t"+item[0]+"\t"+item[1]+"\t"+item[2]+"\t"+item[3])
            else:
                continue
            # if item[0]!="sz.300730":
            #     continue
            kk = test.execute(item[0])
            if kk.isZsm==1:
                print("thread"+str(t)+"\t--------主力、散户、反转信号出现------")
                print(item[0]+"---"+item[1])
            elif kk.isZsm==2:
                print("up")

            if test.avgCostGrad < 0 or kk.isZsm>=1:
                candidateTemp = []
                candidateTemp.append(item[0])
                candidateTemp.append(item[1])
                candidateTemp.append(item[3])
                candidateTemp.append(test.avgCostGrad)
                self.candidate.append(candidateTemp)
                # 插入数据
                sql = "select * from candidate_stock where code='%s' and collect_date='%s'"
                data = (item[0], today)
                cursor.execute(sql % data)
                if len(list(cursor)) == 0:
                    print(item)
                    sql = "INSERT INTO candidate_stock (id, code, name,collect_date,industry,grad,cv,is_down_line,zsm) VALUES ( '%s', '%s','%s', '%s','%s', %.8f, %.8f,%i,%i)"
                    data = (uuid.uuid1(), item[0], item[1],today,item[3],test.avgCostGrad,abs(test.cvValue),test.isDownLine,kk.isZsm)
                    cursor.execute(sql % data)
                elif kk.isZsm > 0:
                    # 开始修正
                    print("修正..")
                    sql = "update candidate_stock set zsm=" + str(kk.isZsm) + " where collect_date='" + today + "' and code='" + item[0] + "' and id!=''"
                    print(sql)
                    cursor.execute(sql)
                connect.commit()
            # 垃圾回收
            del kk, test



    # #扫描潜在可以投资的股票
    def scanStock(self):
        query = QueryStock()
        today=query.todayIsTrue()[0]
        connect = pymysql.Connect(
            host=self.connection.host,
            port=self.connection.port,
            user=self.connection.user,
            passwd=self.connection.passwd,
            db=self.connection.db,
            charset=self.connection.charset
        )
        # 获取游标
        cursor = connect.cursor()
        tableCheckSql = "show tables like 'candidate_stock'"
        cursor.execute(tableCheckSql)
        if len(list(cursor)) == 0:
            createTable = "create table candidate_stock(id varchar(64) primary key not null,code varchar(64),name varchar(64),collect_date varchar(64),industry varchar(64),grad float,cv float,price float,now_price float,profit float,other varchar(45),is_down_line int,zsm int,dl int)"
            cursor.execute(createTable)
        print("-----------------------------scan stock------------------------------------")
        print("start time:" + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
        syn = StockInfoSyn()
        basicStock = syn.getBiscicStock()
        allStocklength=len(basicStock)
        stockCodeList=[]

        i=0
        for j in range(allStocklength):
            item = basicStock[j]
            stockCodeList.append(item)

        self.doScan(1,len(stockCodeList),stockCodeList,today,cursor,connect)
        print("xi")
        print("-----扫描结束-----")



    #按照程度的梯度排序
    def sortByStockGrad(self):
        self.candidate=sorted(self.candidate, key=lambda s: s[3])


    #展示筛选的股票
    def stockShow(self):
        test = ApplicationWithDraw()
        if self.connection.testCode!='':
            print("test one stock:"+self.connection.testCode)
            test.executeForTest(self.connection.testCode,self.currentPath)
        else:
            todayStocks=QueryStock()
            todays=todayStocks.todayRecentDaye(3)
            codes=todayStocks.queryStockByDate(todays)
            for item in codes:
                test = ApplicationWithDraw()
                test.execute(item[0],True,self.currentPath)
                print("image\t"+str(item[1])+"   "+item[0]+"   "+str(item[3]))

    def huiBu(self):
        query = QueryStock()
        connect = pymysql.Connect(
            host=self.connection.host,
            port=self.connection.port,
            user=self.connection.user,
            passwd=self.connection.passwd,
            db=self.connection.db,
            charset=self.connection.charset
        )
        # 获取游标
        cursor = connect.cursor()
        codes=query.queryStock20DayReccently()
        for i in range(len(codes)):
            test = Application()
            kk = test.executeForBc(codes[i][0])
            if kk.isZsm==3:
                # 开始修正
                print(codes[i][0]+"---补充修正3..."+codes[i][1])
                sql = "update candidate_stock set dl=1 where collect_date='" + codes[i][2] + "' and code='" + codes[i][0] + "' and id!=''"
                print(sql)
                cursor.execute(sql)
                connect.commit()
            # 垃圾回收
            del kk, test
        pass

    #突然觉醒
    def soul(self):
        query = QueryStock()
        today = query.todayIsTrue()[0]
        connect = pymysql.Connect(
            host=self.connection.host,
            port=self.connection.port,
            user=self.connection.user,
            passwd=self.connection.passwd,
            db=self.connection.db,
            charset=self.connection.charset
        )
        # 获取游标
        cursor = connect.cursor()
        print("-----------------------------scan soul stock------------------------------------")
        print("start time:" + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
        syn = StockInfoSyn()
        basicStock = syn.getBiscicStock()
        for i in range(len(basicStock)):
            item = basicStock[i]
            if item[1].__contains__("ST"):
                continue
            test = Application()
            kk = test.executeForBc(basicStock[i][0])
            if kk.isZsm==4:
                print("--------亚马逊的河流------")
                print(item[0]+"---"+item[1])
            if kk.isZsm==7:
                print("超级+++++:"+basicStock[i][0])
            if kk.isZsm == 3 or kk.isZsm == 4 or kk.isZsm==5 or kk.isZsm==6 or kk.isZsm==7:
                # 插入数据
                sql = "select * from candidate_stock where code='%s' and collect_date='%s'"
                data = (item[0], today)
                cursor.execute(sql % data)
                if len(list(cursor)) == 0:
                    print(item)
                    sql = "INSERT INTO candidate_stock (id, code, name,collect_date,industry,grad,cv,is_down_line,zsm) VALUES ( '%s', '%s','%s', '%s','%s', %.8f, %.8f,%i,%i)"
                    data = (uuid.uuid1(), item[0], item[1], today, item[3], test.avgCostGrad, abs(test.cvValue),
                            test.isDownLine, kk.isZsm)
                    cursor.execute(sql % data)
                elif kk.isZsm > 0:
                    # 开始修正
                    print("修正..")
                    sql = "update candidate_stock set zsm=" + str(kk.isZsm) + " where collect_date='" + today + "' and code='" + item[0] + "' and id!=''"
                    print(sql)
                    cursor.execute(sql)
                connect.commit()
            # 垃圾回收
            del kk, test
        print("灵魂扫描---finish...")
        print("----------------------soul---end------------------------")
        pass


zm=zMain()
sendEmail=SendEmail()
s=Statistics()
donglifanzhuan=DongliFanzhuan()
#是否是单图测试
if zm.connection.isTest:
    zm.stockShow()
else:
    # 同步历史数据
    zm.synHistoryStock()
    # # #扫描选股
    zm.scanStock()
    #突然觉醒
    zm.soul()
    #动力反转
    donglifanzhuan.donglifanzhuan()
    # # # #股票排名
    zm.sortByStockGrad()
    #统计股票盈利情况
    s.statistic()
    # #回防
    zm.huiBu()
    # # #作图
    zm.stockShow()
    # 分类股票推荐发送
    sendEmail.sendYouCanBuy(zm.currentPath)




