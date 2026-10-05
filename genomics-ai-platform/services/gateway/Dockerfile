FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY services/gateway/src/Gateway/Gateway.csproj src/Gateway/
RUN dotnet restore src/Gateway/Gateway.csproj
COPY services/gateway/src/Gateway src/Gateway
RUN dotnet publish src/Gateway/Gateway.csproj -c Release -o /out --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /out .
ENV ASPNETCORE_URLS=http://+:8080
USER $APP_UID
EXPOSE 8080
ENTRYPOINT ["dotnet", "Gateway.dll"]
