# -*- encoding:utf-8 -*-

import struct
import sys
import os


class Scel2Txt(object):
    # 搜狗的scel词库就是保存的文本的unicode编码，每两个字节一个字符（中文汉字或者英文字母）
    # 找出其每部分的偏移位置即可
    # 主要两部分
    # 1.全局拼音表，貌似是所有的拼音组合，字典序
    #       格式为(index,len,pinyin)的列表
    #       index: 两个字节的整数 代表这个拼音的索引
    #       len: 两个字节的整数 拼音的字节长度
    #       pinyin: 当前的拼音，每个字符两个字节，总长len
    #
    # 2.汉语词组表
    #       格式为(same,py_table_len,py_table,{word_len,word,ext_len,ext})的一个列表
    #       same: 两个字节 整数 同音词数量
    #       py_table_len:  两个字节 整数
    #       py_table: 整数列表，每个整数两个字节,每个整数代表一个拼音的索引
    #
    #       word_len:两个字节 整数 代表中文词组字节数长度
    #       word: 中文词组,每个中文汉字两个字节，总长度word_len
    #       ext_len: 两个字节 整数 代表扩展信息的长度，好像都是10
    #       ext: 扩展信息 前两个字节是一个整数(不知道是不是词频) 后八个字节全是0
    #
    #      {word_len,word,ext_len,ext} 一共重复same次 同音词 相同拼音表

    def __init__(self):
        # 拼音表偏移
        self.startPy = 0x1540
        # 汉语词组表偏移
        self.startChinese = 0x2628
        # 全局拼音表
        self.GPy_Table = {}
        # 解析结果: (词频, 拼音, 中文词组) 的列表
        self.GTable = []

    def byte2str(self, data):
        """将原始字节码转为字符串"""
        i = 0
        length = len(data)
        ret = ''
        while i < length:
            x = data[i:i+2]
            t = chr(struct.unpack('H', x)[0])
            if t == '\r':
                ret += '\n'
            elif t != ' ':
                ret += t
            i += 2
        return ret

    def getPyTable(self, data):
        """获取拼音表"""
        if data[0:4] != b"\x9D\x01\x00\x00":
            return None
        data = data[4:]
        pos = 0
        length = len(data)
        while pos < length:
            index = struct.unpack('H', data[pos:pos+2])[0]
            pos += 2
            l = struct.unpack('H', data[pos:pos+2])[0]
            pos += 2
            py = self.byte2str(data[pos:pos+l])
            self.GPy_Table[index] = py
            pos += l

    def getWordPy(self, data):
        """获取一个词组的拼音"""
        pos = 0
        length = len(data)
        ret = ''
        while pos < length:
            index = struct.unpack('H', data[pos:pos+2])[0]
            ret += self.GPy_Table[index]
            pos += 2
        return ret

    def getChinese(self, data):
        """读取中文表"""
        pos = 0
        length = len(data)
        while pos < length:
            # 同音词数量
            same = struct.unpack('H', data[pos:pos+2])[0]

            # 拼音索引表长度
            pos += 2
            py_table_len = struct.unpack('H', data[pos:pos+2])[0]

            # 拼音索引表
            pos += 2
            py = self.getWordPy(data[pos:pos+py_table_len])

            # 中文词组
            pos += py_table_len
            for i in range(same):
                # 中文词组长度
                c_len = struct.unpack('H', data[pos:pos+2])[0]
                # 中文词组
                pos += 2
                word = self.byte2str(data[pos:pos+c_len])
                # 扩展数据长度
                pos += c_len
                ext_len = struct.unpack('H', data[pos:pos+2])[0]
                # 词频
                pos += 2
                count = struct.unpack('H', data[pos:pos+2])[0]
                # 保存
                self.GTable.append((count, py, word))
                # 到下个词的偏移位置
                pos += ext_len

    def deal(self, file_name):
        self.GTable = []
        print('-' * 60)
        with open(file_name, 'rb') as f:
            data = f.read()

        if data[0:12] != b"\x40\x15\x00\x00\x44\x43\x53\x01\x01\x00\x00\x00":
            print("确认你选择的是搜狗(.scel)词库?")
            sys.exit(0)

        # 读取词库信息
        dict_name = self.byte2str(data[0x130:0x338]).replace('\x00', '').strip()
        dict_type = self.byte2str(data[0x338:0x540]).replace('\x00', '').strip()
        dict_desc = self.byte2str(data[0x540:0xd40]).replace('\x00', '').strip()
        # 示例词（不一定准确，仅供预览）
        dict_sample = self.byte2str(data[0xd40:self.startPy]).replace('\x00', '').strip()

        self.getPyTable(data[self.startPy:self.startChinese])
        self.getChinese(data[self.startChinese:])

        return dict_name, dict_type, dict_desc, dict_sample


if __name__ == '__main__':
    import sys
    scel_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "scel")
    out_dir = sys.argv[2] if len(sys.argv) > 2 else scel_dir
    os.makedirs(out_dir, exist_ok=True)

    scel_list = [os.path.join(scel_dir, f) for f in os.listdir(scel_dir) if f.endswith('.scel')]

    if not scel_list:
        print("未找到 .scel 文件")
        sys.exit(1)

    scel2txt = Scel2Txt()
    for _file in scel_list:
        meta = scel2txt.deal(_file)
        dict_name = meta[0] if meta else ''
        result = [x[2] for x in scel2txt.GTable]
        basename = os.path.splitext(os.path.basename(_file))[0]
        out_path = os.path.join(out_dir, basename + ".txt")
        with open(out_path, "w", encoding="utf-8") as fout:
            if dict_name:
                fout.write(f"# 词库名: {dict_name}\n")
            fout.write("\n".join(result))
        print(f"输出: {out_path} ({len(result)} 条) [{dict_name}]")
