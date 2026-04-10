# ZeroNews内网穿刺配置

[ZeroNews（零讯）内网穿透｜企业级内网穿透专家｜远程安全连接｜反向代理工具-ZeroNews官网](https://zeronews.cc/)

## 1.登录和下载

![1](..\image\ZeroNews1.jpg)

下载对应的版本

![2](..\image\ZeroNews2.jpg)

下载完毕后进入到对应的exe所在的文件夹使用cmd执行下面的命名

```python
zeronews.exe set token xxxxxxxxxxxxxx
```

![3](..\image\ZeroNews3.jpg)

执行完上面的命名后再执行下面的命令：

```python
zeronews.exe start
```

执行完成后，在Agent下面会出现我们对应的设备

![4](..\image\ZeroNews4.jpg)

## 2.添加端口映射机制

操作完上面的流程后，我们点击**映射**，这个时候界面应该是空着的，点击添加映射

![5](..\image\ZeroNews5.jpg)

1.点击选择Agent会出现我们的设备，都选择**HTTPS**

2.这里的公网访问地址应该有两个可以随便选

3.映射带宽都只能**配置1Mbps**，**很慢**（如果自己有选择可以使用别的穿刺工具）

4.内网端口：需要映射**两个端口（前端端口：5173，后端端口：8000）**，这两个接口在项目中的定义会在本文档最后补充

![6](..\image\ZeroNews6.jpg)

## 3.得到映射的地址

完成了上面的操作之后就会得到**两个地址，前后端的映射地址**

![7](..\image\ZeroNews7.jpg)



## 补充：

在我们配置文件中会有端口号，这个会在操作中详细讲

![8](..\image\Set1.jpg)



也可以使用其它的工具进行映射如**ngork**，免费版只能使用一个映射